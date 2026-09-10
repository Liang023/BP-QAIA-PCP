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
        for h in range(j):
            a = candidates[h]
            if start < a[3] and a[2] < end:
                for k in range(C):
                    model.addConstr(x[j, k] + x[h, k] <= 1)
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
                  lower_bound=model.ObjBound, schedule=schedule)
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
    for v in vehicles:
        cs = v["candidates"]
        if not cs or len({c["candidate_id"] for c in cs}) != len(cs):
            raise ValueError("空候选或重复candidate_id")
        for c in cs:
            if not (0 <= c["start"] < c["end"] <= data["time_horizon"]):
                raise ValueError("候选时间越界")
            if c["end"] - c["start"] != v["duration"]:
                raise ValueError("候选时长不一致")


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
    with log.open("x", encoding="utf-8") as f:
        with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
            try:
                raw = instance_path.read_bytes()
                record["instance_sha256"] = hashlib.sha256(raw).hexdigest()
                data = json.loads(raw)
                check_input(data)
                record["vehicles"] = len(data["vehicles"])
                record["vertices"] = sum(len(v["candidates"]) for v in data["vehicles"])
                record["git_sha"] = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], text=True).strip()
                record["git_diff_sha256"] = hashlib.sha256(subprocess.check_output(
                    ["git", "diff", "HEAD"])).hexdigest()
                # 此指纹不包含未跟踪文件；另记录关键脚本文件字节指纹。
                record["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
                import gurobipy as gp
                record["gurobi"] = gp.gurobi.version()
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
                    if result["status"] == "optimal" and bp.best_schedule is None:
                        raise ValueError("声称optimal但没有通过排程校验")
            except Exception as exc:
                record.update(status="error", error=repr(exc))
                traceback.print_exc()
    out.write_text(json.dumps(clean(record), ensure_ascii=False, indent=2,
                              allow_nan=False), encoding="utf-8")
    print(f"结果: {out}\n日志: {log}\n状态: {record['status']}")


if __name__ == "__main__":
    main()