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


def compact(data, limit, *, deadline=None, recorder=None):
    import gurobipy as gp
    from cg.deadline import remaining_seconds
    start = time.perf_counter()
    deadline = start+limit if deadline is None else deadline
    model = None
    callback_errors = []
    try:
        remaining_seconds(deadline, "Before compact construction")
        candidates = [(v["id"], c["candidate_id"], c["start"], c["end"])
                      for v in data["vehicles"] for c in v["candidates"]]
        C = data["num_chargers"]
        model = gp.Model("independent_candidate_milp")
        model.Params.OutputFlag = 0
        model.Params.Threads = 1
        model.Params.Seed = 0
        model.Params.MIPGap = 0
        model.Params.MIPGapAbs = 0
        x = model.addVars(len(candidates), C, vtype=gp.GRB.BINARY)
        T = model.addVar(lb=0, name="T")
        for vehicle in data["vehicles"]:
            remaining_seconds(deadline, "Compact vehicle constraints")
            model.addConstr(gp.quicksum(x[j, k]
                for j, c in enumerate(candidates) if c[0] == vehicle["id"]
                for k in range(C)) == 1)
        active = {}
        for j, (_, _, start_slot, end) in enumerate(candidates):
            remaining_seconds(deadline, "Compact candidate constraints")
            model.addConstr(T >= end * gp.quicksum(x[j, k] for k in range(C)))
            for slot in range(start_slot, end):
                active.setdefault(slot, []).append(j)
        for slot, indices in sorted(active.items()):
            remaining_seconds(deadline, "Compact occupancy constraints")
            if len(indices) > 1:
                for k in range(C):
                    model.addConstr(gp.quicksum(x[j, k] for j in indices) <= 1)
        model.setObjective(T, gp.GRB.MINIMIZE)
        keys = list(x)
        variables = [x[key] for key in keys]

        def unpack(values):
            rows = [[] for _ in range(C)]
            for (j, k), value in zip(keys, values):
                if value > 0.5:
                    c = candidates[j]
                    rows[k].append(dict(vehicle_id=c[0], candidate_id=c[1], start=c[2], end=c[3]))
            return [sorted(row, key=lambda c: c["start"]) for row in rows if row]

        def callback(m, where):
            if where != gp.GRB.Callback.MIPSOL or recorder is None:
                return
            if time.perf_counter() > deadline:
                m.terminate()
                return
            try:
                schedule = unpack(m.cbGetSolution(variables))
                objective = max(c["end"] for row in schedule for c in row)
                recorder.record(schedule, objective, "compact_mipsol")
            except Exception as exc:
                callback_errors.append(exc)
                m.terminate()

        model.Params.TimeLimit = remaining_seconds(deadline, "Compact optimize")
        model.optimize(callback)
        if callback_errors:
            raise callback_errors[0]
        schedule = unpack([v.X for v in variables]) if model.SolCount else []
        if schedule and recorder is not None:
            recorder.record(schedule, max(c["end"] for row in schedule for c in row), "compact_final")
        finished = time.perf_counter()
        status = ("optimal" if model.Status == gp.GRB.OPTIMAL and finished <= deadline
                  else "infeasible_proven" if model.Status == gp.GRB.INFEASIBLE and finished <= deadline
                  else "time_limit" if finished >= deadline or model.Status == gp.GRB.TIME_LIMIT
                  else f"gurobi_status_{model.Status}")
        if recorder is not None:
            schedule = recorder.history[-1]["schedule"] if recorder.history else []
        return dict(status=status,
                    objective=max(c["end"] for row in schedule for c in row) if schedule else None,
                    lower_bound=model.ObjBound, schedule=schedule,
                    compact_formulation="integer_slot_occupancy_v1",
                    compact_variables=model.NumVars, compact_constraints=model.NumConstrs)
    finally:
        if model is not None:
            model.dispose()

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
    p.add_argument("--checkpoints", type=float, nargs="*", default=[10, 30, 60, 120, 300])
    args = p.parse_args()
    if not math.isfinite(args.limit) or args.limit <= 0:
        p.error("limit must be positive and finite")
    if any(not math.isfinite(t) or t < 0 for t in args.checkpoints):
        p.error("checkpoints must be finite and nonnegative")
    instance_path, out = Path(args.instance).resolve(), Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    log, trace = out.with_suffix(".log"), out.with_suffix(".incumbents.jsonl")
    if any(path.exists() for path in (out, log, trace)):
        raise FileExistsError("输出已存在，请使用新的--out")
    os.chdir(ROOT)
    os.environ["BPC_DUMP_LP"] = "0"
    from cg.anytime import IncumbentRecorder, snapshots
    from cg.deadline import remaining_seconds
    from validation.ev_solution import validate_json_schedule
    record = dict(method=args.method, seed=args.seed, limit=args.limit,
                  instance=str(instance_path), python=sys.version,
                  platform=platform.platform(), threads=1, gurobi_seed=0,
                  timing_scope="after_input_and_imports_before_graph_and_model",
                  verbose=os.getenv("BPC_VERBOSE", "0") == "1")
    recorder = bp = None
    workflow_start = time.perf_counter()
    budget_start = None
    with log.open("x", encoding="utf-8") as f:
        with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
            try:
                raw = instance_path.read_bytes()
                record["instance_sha256"] = hashlib.sha256(raw).hexdigest()
                data = json.loads(raw)
                check_input(data)
                record.update(vehicles=len(data["vehicles"]),
                    vertices=sum(len(v["candidates"]) for v in data["vehicles"]),
                    schema_version=data.get("schema_version", "legacy"),
                    data_metadata=data.get("metadata"))
                try:
                    record["git_sha"] = subprocess.check_output(
                        ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
                    record["git_diff_sha256"] = hashlib.sha256(subprocess.check_output(
                        ["git", "diff", "HEAD"], stderr=subprocess.DEVNULL)).hexdigest()
                except (OSError, subprocess.CalledProcessError):
                    record.update(git_sha=None, git_diff_sha256=None)
                record["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
                source_files = sorted(path for folder in ("bpc", "cg", "config", "ev", "model",
                    "qaia", "test", "validation") for path in (ROOT/folder).rglob("*.py"))
                digest = hashlib.sha256()
                for path in source_files:
                    digest.update(path.relative_to(ROOT).as_posix().encode()+b"\0")
                    digest.update(path.read_bytes()+b"\0")
                record["source_sha256"] = digest.hexdigest()
                from config.qaia_runtime import pricing_options
                record["qaia_config"] = (dict(scope="root", **pricing_options(),
                    column_policy=os.getenv("QAIA_COLUMN_POLICY", "combined"))
                    if args.method == "qaia_root" else None)
                record["exact_pricing_config"] = (dict(
                    pool_search_mode=int(os.getenv("EXACT_POOL_SEARCH_MODE", "2")),
                    pool_solutions=10, mip_gap=0.0, mip_gap_abs=0.0)
                    if args.method != "compact" else None)
                record["restricted_mip_config"] = dict(
                    enabled=os.getenv("BPC_RMP_MIP", "1") == "1", scope="root",
                    every=int(os.getenv("BPC_RMP_MIP_EVERY", "20")),
                    seconds=float(os.getenv("BPC_RMP_MIP_SECONDS", "0.5")),
                    fraction=float(os.getenv("BPC_RMP_MIP_FRACTION", "0.1")))
                import gurobipy as gp
                record["gurobi"] = gp.gurobi.version()
                if args.method != "compact":
                    from ev.ev_to_pcp import ev_json_to_instance
                    from bpc.branch_and_price import BranchAndPrice
                if args.method == "qaia_root" and record["qaia_config"]["heuristic_provider"] == "qaia":
                    import qaia  # dependency preparation is outside the algorithm budget
                budget_start = time.perf_counter()
                deadline = budget_start+args.limit
                recorder = IncumbentRecorder(budget_start, deadline,
                    validator=lambda schedule, value: validate_json_schedule(data, schedule, value),
                    path=trace, metadata=dict(instance_sha256=record["instance_sha256"],
                        method=args.method, seed=args.seed, source_sha256=record["source_sha256"]))
                if args.method == "compact":
                    record.update(compact(data, args.limit, deadline=deadline, recorder=recorder))
                else:
                    t0 = time.perf_counter()
                    inst = ev_json_to_instance(data, deadline=deadline)
                    record["graph_seconds"] = time.perf_counter()-t0
                    remaining_seconds(deadline, "After graph construction")
                    bp = BranchAndPrice(inst.graph, inst.charger_num,
                        time_limit=args.limit, use_qaia=args.method == "qaia_root", qaia_seed=args.seed)
                    result = bp.solve(start_time=budget_start, deadline=deadline, recorder=recorder)
                    record.update(status=result["status"], objective=result["objective_value"],
                        statistics=result["statistics"], error=result.get("error"),
                        validated_schedule=bp.best_schedule, schedule_makespan=bp.best_schedule_makespan)
                    for key in ("total_pricing_time", "total_qaia_time", "total_hybrid_exact_time",
                                "total_qaia_calls", "total_hybrid_exact_calls", "qaia_nodes", "exact_only_nodes"):
                        record[key] = getattr(bp, key)
            except TimeoutError as exc:
                record.update(status="time_limit", error=str(exc))
            except Exception as exc:
                record.update(status="error", error=repr(exc))
                traceback.print_exc()
            finally:
                if budget_start is not None:
                    record["wall_seconds"] = time.perf_counter()-budget_start
                    record["budget_overrun_seconds"] = max(0.0, record["wall_seconds"]-args.limit)
                if recorder is not None:
                    record.update(recorder.fields())
                    history = recorder.history
                    if history:
                        last = history[-1]
                        record.update(objective=last["objective"], schedule_makespan=last["objective"],
                                      validation_passed=True)
                        if args.method == "compact":
                            record["schedule"] = last["schedule"]
                        else:
                            record["validated_schedule"] = dict(schedule=last["schedule"],
                                makespan=last["objective"])
                    else:
                        record.update(objective=None, validation_passed=False)
                    checkpoints = sorted({t for t in args.checkpoints if t <= args.limit} | {args.limit})
                    record["budget_snapshots"] = snapshots(history, checkpoints)
                else:
                    record.update(has_feasible_solution=False, objective=None, validation_passed=False)
                if record.get("status") == "optimal" and not record.get("validation_passed"):
                    record.update(status="error", error="optimal without a validated in-budget schedule")
                record["termination_reason"] = record["status"]
                record["workflow_seconds"] = time.perf_counter()-workflow_start
    out.write_text(json.dumps(clean(record), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(f"结果: {out}\n轨迹: {trace}\n状态: {record['status']}\n可行目标: {record.get('objective')}")


if __name__ == "__main__":
    main()
