"""ACN sessions -> small, offline, homogeneous-charger PCP instances."""
import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, time, timezone
from decimal import Decimal, ROUND_CEILING
from email.utils import parsedate_to_datetime
import hashlib
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo


def utc_time(value):
    if not isinstance(value, str):
        raise ValueError("timestamp_missing")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        stamp = parsedate_to_datetime(value)
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("timezone_missing")
    return stamp.astimezone(timezone.utc)


def positive_decimal(value):
    number = Decimal(str(value))
    if not number.is_finite() or number <= 0:
        raise ValueError("energy_or_power_not_positive")
    return number


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--raw", required=True)
    p.add_argument("--date", required=True, help="Local arrival date, YYYY-MM-DD")
    p.add_argument("--out", required=True)
    p.add_argument("--slot-minutes", type=int, default=15)
    p.add_argument("--power-kw", default="7")
    p.add_argument("--chargers", type=int, default=2)
    p.add_argument("--max-sessions", type=int, default=6)
    p.add_argument("--max-vertices", type=int, default=300)
    p.add_argument("--max-stay-hours", type=int, default=48)
    args = p.parse_args()
    if min(args.slot_minutes, args.chargers, args.max_sessions,
           args.max_vertices, args.max_stay_hours) <= 0:
        p.error("Integer parameters must be positive")
    power = positive_decimal(args.power_kw)
    day = date.fromisoformat(args.date)
    raw_path, out = Path(args.raw), Path(args.out)
    audit_path = out.with_suffix(".audit.json")
    if out.exists() or audit_path.exists():
        raise FileExistsError("Use a new output path; never overwrite an experiment")
    raw = raw_path.read_bytes()
    payload = json.loads(raw)
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict) and isinstance(payload.get("_items"), list):
        records = payload["_items"]
        if (payload.get("_links") or {}).get("next"):
            raise ValueError("Incomplete API page: download and combine ALL pages first")
        total = (payload.get("_meta") or {}).get("total")
        if total is not None and int(total) != len(records):
            raise ValueError("API total differs from record count")
    else:
        raise ValueError("Expected a session list or an ACN _items object")
    if not records or any(not isinstance(row, dict) for row in records):
        raise ValueError("Expected a nonempty list of session objects")
    # Do not silently mix different sites or timezones.
    site_ids = {str(r["siteID"]) for r in records if r.get("siteID") is not None}
    zones = {r["timezone"] for r in records if r.get("timezone")}
    if len(site_ids) != 1 or len(zones) != 1:
        raise ValueError("Export exactly one site with one explicit timezone")
    site_id, zone_name = next(iter(site_ids)), next(iter(zones))
    zone = ZoneInfo(zone_name)
    origin = datetime.combine(day, time.min, tzinfo=zone).astimezone(timezone.utc)
    step = args.slot_minutes * 60
    audit, groups = [], defaultdict(list)

    def note(index, row, reason):
        audit.append(dict(raw_index=index, session_id=row.get("sessionID"), reason=reason))

    for index, row in enumerate(records):
        sid = row.get("sessionID")
        if not isinstance(sid, str) or not sid.strip():
            note(index, row, "invalid_missing_session_id")
        else:
            groups[sid].append((index, row))

    usable = []
    essential = ("siteID", "stationID", "timezone", "connectionTime",
                 "disconnectTime", "kWhDelivered")
    for sid, group in sorted(groups.items()):
        signatures = {json.dumps({k: r.get(k) for k in essential}, sort_keys=True)
                      for _, r in group}
        if len(signatures) != 1:
            for index, row in group:
                note(index, row, "invalid_conflicting_duplicate")
            continue
        index, row = group[0]
        for duplicate_index, duplicate in group[1:]:
            note(duplicate_index, duplicate, "duplicate_same_model_fields")
        try:
            if str(row.get("siteID")) != site_id or row.get("timezone") != zone_name:
                raise ValueError("missing_site_or_timezone")
            connection = utc_time(row.get("connectionTime"))
            departure = utc_time(row.get("disconnectTime"))
            energy = Decimal(str(row.get("kWhDelivered")))
            if not energy.is_finite() or energy < 0:
                raise ValueError("invalid_delivered_energy")
            if departure <= connection:
                raise ValueError("nonpositive_stay")
        except (ValueError, TypeError, ArithmeticError, OverflowError) as exc:
            note(index, row, "invalid_fields:" + str(exc))
            continue
        if energy == 0:
            note(index, row, "excluded_zero_delivered_energy")
            continue
        if connection.astimezone(zone).date() != day:
            note(index, row, "outside_arrival_date")
            continue
        if (departure - connection).total_seconds() > args.max_stay_hours * 3600:
            note(index, row, "pilot_excluded_long_stay")
            continue
        arrival_slot = math.ceil((connection-origin).total_seconds() / step)
        departure_slot = math.floor((departure-origin).total_seconds() / step)
        duration = int((energy * 3600 / (power * step)).to_integral_value(
            rounding=ROUND_CEILING))
        if arrival_slot + duration > departure_slot:
            note(index, row, "model_excluded_insufficient_discrete_window")
            continue
        vehicle = dict(session_id=sid, station_id=row.get("stationID"),
                       connection_utc=connection.isoformat(),
                       disconnect_utc=departure.isoformat(), energy_kwh=str(energy),
                       arrival=arrival_slot, departure=departure_slot, duration=duration)
        usable.append((connection, sid, index, row, vehicle))
    usable.sort(key=lambda item: (item[0], item[1]))
    selected = usable[:args.max_sessions]
    for _, _, index, row, _ in usable[args.max_sessions:]:
        note(index, row, "pilot_not_selected_first_n")
    vehicles = []
    for vehicle_id, (_, _, index, row, vehicle) in enumerate(selected):
        vehicle["id"] = vehicle_id
        vehicle["candidates"] = [dict(candidate_id=j, start=s, end=s+vehicle["duration"])
            for j, s in enumerate(range(vehicle["arrival"],
                                        vehicle["departure"]-vehicle["duration"]+1))]
        vehicles.append(vehicle)
        note(index, row, "selected")
    count = sum(len(v["candidates"]) for v in vehicles)
    blocked = ("no_eligible_sessions" if not vehicles else
               "candidate_limit_exceeded" if count > args.max_vertices else None)
    metadata = dict(raw_sha256=hashlib.sha256(raw).hexdigest(),
                    converter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    raw_filename=raw_path.name, site_id=site_id,
                    timezone=zone_name, local_arrival_date=day.isoformat(),
                    origin_utc=origin.isoformat(), slot_minutes=args.slot_minutes,
                    power_kw=str(power), energy_basis="observed_kWhDelivered",
                    charger_basis="assumed_homogeneous_pool",
                    selection="first_n_by_connection_time_then_session_id",
                    max_sessions=args.max_sessions, max_vertices=args.max_vertices,
                    max_stay_hours=args.max_stay_hours)
    out.parent.mkdir(parents=True, exist_ok=True)
    report = dict(status="blocked" if blocked else "converted", reason=blocked,
                  metadata=metadata, raw_records=len(records),
                  eligible_sessions=len(usable), selected_sessions=len(vehicles),
                  vertices=count, counts=dict(Counter(x["reason"] for x in audit)),
                  records=sorted(audit, key=lambda x: x["raw_index"]))
    with audit_path.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, allow_nan=False)
    if blocked:
        raise ValueError(f"{blocked}; inspect {audit_path}; do not sample candidate intervals")
    instance = dict(schema_version="acn-derived-v1", name=out.stem,
                    time_unit="slot", time_horizon=max(v["departure"] for v in vehicles),
                    num_vehicles=len(vehicles), num_chargers=args.chargers,
                    metadata=metadata, vehicles=vehicles)
    with out.open("x", encoding="utf-8") as f:
        json.dump(instance, f, ensure_ascii=False, indent=2, allow_nan=False)
    print(f"{out}: {len(vehicles)} sessions, {count} vertices; audit: {audit_path}")


if __name__ == "__main__":
    main()