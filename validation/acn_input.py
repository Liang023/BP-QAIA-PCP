"""Independent validation of ACN-derived temporal and energy semantics."""
from datetime import date, datetime, time, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from zoneinfo import ZoneInfo


def validate_acn_input(data):
    if data.get("schema_version") != "acn-derived-v1":
        return
    meta = data["metadata"]
    step_minutes = meta["slot_minutes"]
    if type(step_minutes) is not int or step_minutes <= 0:
        raise ValueError("ACN slot_minutes must be a positive integer")
    power = Decimal(str(meta["power_kw"]))
    if not power.is_finite() or power <= 0:
        raise ValueError("ACN power must be positive and finite")
    if meta["energy_basis"] != "observed_kWhDelivered":
        raise ValueError("Unexpected energy basis")
    if meta["charger_basis"] != "assumed_homogeneous_pool":
        raise ValueError("Unexpected charger model")

    def stamp(value):
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("ACN timestamp must include timezone")
        return parsed.astimezone(timezone.utc)

    # Integer microseconds avoid float rounding at grid boundaries.
    def seconds(delta):
        micros = (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds
        return Decimal(micros) / 1000000

    origin = stamp(meta["origin_utc"])
    local_day = date.fromisoformat(meta["local_arrival_date"])
    zone = ZoneInfo(meta["timezone"])
    expected_origin = datetime.combine(local_day, time.min, tzinfo=zone)
    if origin != expected_origin.astimezone(timezone.utc):
        raise ValueError("ACN origin must be local arrival-day midnight")
    step = Decimal(step_minutes * 60)
    slot_energy = power * step / 3600
    ids = [v["session_id"] for v in data["vehicles"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate original sessions")
    for v in data["vehicles"]:
        connection, departure = stamp(v["connection_utc"]), stamp(v["disconnect_utc"])
        if connection.astimezone(zone).date() != local_day or departure <= connection:
            raise ValueError("ACN original time window is invalid")
        expected_r = int((seconds(connection-origin) / step).to_integral_value(
            rounding=ROUND_CEILING))
        expected_d = int((seconds(departure-origin) / step).to_integral_value(
            rounding=ROUND_FLOOR))
        energy = Decimal(str(v["energy_kwh"]))
        if not energy.is_finite() or energy <= 0:
            raise ValueError("ACN delivered energy must be positive and finite")
        length = v["duration"]
        if type(length) is not int or length <= 0:
            raise ValueError("ACN duration must be a positive integer")
        if not (slot_energy * (length-1) < energy <= slot_energy * length):
            raise ValueError("ACN duration does not match energy and assumed power")
        if (v["arrival"], v["departure"]) != (expected_r, expected_d):
            raise ValueError("ACN window rounding is incorrect")
        if not (0 <= expected_r < expected_d <= data["time_horizon"]):
            raise ValueError("ACN window outside horizon")
        if length > expected_d - expected_r:
            raise ValueError("ACN window too short")
        expected = {(s, s+length) for s in range(expected_r, expected_d-length+1)}
        observed = [(c["start"], c["end"]) for c in v["candidates"]]
        if len(observed) != len(set(observed)) or set(observed) != expected:
            raise ValueError("ACN candidates must enumerate the complete window")