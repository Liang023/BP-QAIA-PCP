import argparse
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def compact(data, limit):
    import gurobipy as gp
    candidates = [(v["id"], c["candidate_id"], c["start"], c["end"])
                  for v in data["vehicles"] for c in v["candidates"]]
    C = data["num_chargers"]
    model = gp.Model("independent_candidate_milp")
    model.Params.OutputFlag = 0
    model.Params.Threads = 1
    model.Params.Seed = 0
    model.Params.MIPGap = 0
    model.Params.MIPGapAbs = 0
    model.Params.TimeLimit = limit
    x = model.addVars(len(candidates), C, vtype=gp.GRB.BINARY)
    T = model.addVar(lb=0, name="T")
    for vehicle in data["vehicles"]:
        model.addConstr(gp.quicksum(x[j, k]
            for j, c in enumerate(candidates) if c[0] == vehicle["id"]
            for k in range(C)) == 1)
    for j, (_, _, start, end) in enumerate(candidates):
        model.addConstr(T >= end * gp.quicksum(x[j, k] for k in range(C)))
    # Integer, half-open intervals: sharing a slot is exactly overlapping.
    active = {}
    for j, (_, _, start, end) in enumerate(candidates):
        for slot in range(start, end):
            active.setdefault(slot, []).append(j)
    for slot, indices in sorted(active.items()):
        if len(indices) > 1:
            for k in range(C):
                model.addConstr(gp.quicksum(x[j, k] for j in indices) <= 1,
                                name=f"occupancy_{k}_{slot}")
    model.setObjective(T, gp.GRB.MINIMIZE)
    model.optimize()
    schedule = []
    if model.SolCount:
        for k in range(C):
            row = [dict(vehicle_id=c[0], candidate_id=c[1], start=c[2], end=c[3])
                   for j, c in enumerate(candidates) if x[j, k].X > 0.5]
            if row:
                schedule.append(sorted(row, key=lambda c: c["start"]))
    result = dict(status="optimal" if model.Status == gp.GRB.OPTIMAL
                  else f"gurobi_status_{model.Status}",
                  objective=model.ObjVal if model.SolCount else None,
                  lower_bound=model.ObjBound, schedule=schedule,
                  compact_formulation="integer_slot_occupancy_v1",
                  compact_variables=model.NumVars, compact_constraints=model.NumConstrs)
    model.dispose()
    return result

def check_input(data):
    vehicles = data["vehicles"]
    if not vehicles or [v["id"] for v in vehicles] != list(range(len(vehicles))):
        raise ValueError("本轮要求非空、按0..N-1连续编号的车辆")
    if data["num_vehicles"] != len(vehicles):
        raise ValueError("车辆数量元数据不一致")
    if type(data["num_chargers"]) is not int or data["num_chargers"] < 1:
        raise ValueError("桩数必须为正整数")
    horizon = data["time_horizon"]
    if type(horizon) is not int or horizon <= 0:
        raise ValueError("本阶段要求正整数time_horizon")
    for v in vehicles:
        if type(v["id"]) is not int or type(v["duration"]) is not int or v["duration"] <= 0:
            raise ValueError("车辆编号和充电时长必须为整数，时长须大于0")
        cs = v["candidates"]
        if not cs or len({c["candidate_id"] for c in cs}) != len(cs):
            raise ValueError("空候选或重复candidate_id")
        for c in cs:
            if any(type(c[k]) is not int for k in ("candidate_id", "start", "end")):
                raise ValueError("本阶段候选必须使用整数编号和整数时间槽")
            if not (0 <= c["start"] < c["end"] <= horizon):
                raise ValueError("候选时间越界")
            if c["end"] - c["start"] != v["duration"]:
                raise ValueError("候选时长不一致")
    if data.get("schema_version") in ("synthetic-v1", "acn-derived-v1"):
        for v in vehicles:
            r, d, duration = v["arrival"], v["departure"], v["duration"]
            if any(type(z) is not int for z in (r, d, duration)):
                raise ValueError("v1使用整数时间槽")
            if not (0 <= r < d <= horizon and 0 < duration <= d-r):
                raise ValueError("v1时间窗非法")
            expected = {(s, s+duration) for s in range(r, d-duration+1)}
            observed = [(c["start"], c["end"]) for c in v["candidates"]]
            if len(observed) != len(set(observed)) or set(observed) != expected:
                raise ValueError("v1候选重复或没有枚举完整窗口")
    if data.get("schema_version") == "acn-derived-v1":
        from validation.acn_input import validate_acn_input
        validate_acn_input(data)

def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--instance", required=True)
    p.add_argument("--method", choices=["compact", "exact", "qaia_root"], required=True)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--limit", type=float, default=120)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    instance_path = Path(args.instance).resolve()
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    log = out.with_suffix(".log")
    if out.exists() or log.exists():
        raise FileExistsError("输出已存在，请使用新的--out，防止覆盖原始记录")
    os.chdir(ROOT)
    os.environ["BPC_DUMP_LP"] = "0"
    record = dict(method=args.method, seed=args.seed, limit=args.limit,
                  instance=str(instance_path), python=sys.version,
                  platform=platform.platform(), threads=1, gurobi_seed=0)
    record["verbose"] = os.getenv("BPC_VERBOSE", "0") == "1"
    with log.open("x", encoding="utf-8") as f:
        with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
            try:
                raw = instance_path.read_bytes()
                record["instance_sha256"] = hashlib.sha256(raw).hexdigest()
                data = json.loads(raw)
                check_input(data)
                record["vehicles"] = len(data["vehicles"])
                record["vertices"] = sum(len(v["candidates"]) for v in data["vehicles"])
                record["schema_version"] = data.get("schema_version", "legacy")
                record["data_metadata"] = data.get("metadata")
                record["git_sha"] = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], text=True).strip()
                record["git_diff_sha256"] = hashlib.sha256(subprocess.check_output(
                    ["git", "diff", "HEAD"])).hexdigest()
                # 此指纹不包含未跟踪文件；另记录关键脚本文件字节指纹。
                record["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

                source_files = sorted(
                    path for folder in ("bpc", "cg", "config", "ev", "model",
                                         "qaia", "test", "validation")
                    for path in (ROOT / folder).rglob("*.py")
                )
                digest = hashlib.sha256()
                for path in source_files:
                    digest.update(path.relative_to(ROOT).as_posix().encode())
                    digest.update(b"\0")
                    digest.update(path.read_bytes())
                    digest.update(b"\0")
                record["source_sha256"] = digest.hexdigest()
                record["qaia_config"] = dict(
                    scope="root", exact_mode="always", algorithm="BSB",
                    n_iter=200, batch_size=10, max_columns=3,
                    backend="cpu-float32") if args.method == "qaia_root" else None
                if record["qaia_config"] is not None:
                    record["qaia_config"]["column_policy"] = os.getenv(
                        "QAIA_COLUMN_POLICY", "combined")
                import gurobipy as gp
                record["gurobi"] = gp.gurobi.version()
                workflow_start = time.perf_counter()
                if args.method == "compact":
                    t0 = time.perf_counter()
                    record.update(compact(data, args.limit))
                    record["wall_seconds"] = time.perf_counter() - t0
                else:
                    from ev.ev_to_pcp import ev_json_to_instance
                    from bpc.branch_and_price import BranchAndPrice
                    t0 = time.perf_counter()
                    inst = ev_json_to_instance(data)
                    record["graph_seconds"] = time.perf_counter() - t0
                    bp = BranchAndPrice(inst.graph, inst.charger_num,
                        time_limit=args.limit, use_qaia=args.method == "qaia_root",
                        qaia_seed=args.seed)
                    t0 = time.perf_counter()
                    result = bp.solve()
                    record["wall_seconds"] = time.perf_counter() - t0
                    record.update(status=result["status"],
                                  objective=result.get("objective_value"),
                                  statistics=result.get("statistics"),
                                  error=result.get("error"),
                                  validated_schedule=bp.best_schedule,
                                  schedule_makespan=bp.best_schedule_makespan)
                    for key in ("total_pricing_time", "total_qaia_time",
                                "total_hybrid_exact_time", "total_qaia_calls",
                                "total_hybrid_exact_calls", "qaia_nodes", "exact_only_nodes"):
                        record[key] = getattr(bp, key)
                schedule = (record.get("schedule") if args.method == "compact"
                            else (record.get("validated_schedule") or {}).get("schedule"))
                if schedule:
                    from validation.ev_solution import validate_json_schedule
                    schedule_value = max(c["end"] for row in schedule for c in row)
                    validate_json_schedule(data, schedule, schedule_value)
                    record["schedule_makespan"] = schedule_value
                    record["validation_passed"] = True
                    if record["status"] == "optimal":
                        if abs(schedule_value - record["objective"]) > 1e-6:
                            raise ValueError("optimal目标与物理排程makespan不一致")
                elif record["status"] == "optimal":
                    raise ValueError("声称optimal但没有排程")
                record["workflow_seconds"] = time.perf_counter() - workflow_start
            except Exception as exc:
                record.update(status="error", error=repr(exc))
                traceback.print_exc()
    out.write_text(json.dumps(clean(record), ensure_ascii=False, indent=2,
                              allow_nan=False), encoding="utf-8")
    print(f"结果: {out}\n日志: {log}\n状态: {record['status']}")


if __name__ == "__main__":
    main()