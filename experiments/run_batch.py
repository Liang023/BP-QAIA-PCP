"""Collect all planned outcomes, including timeouts; never write PASS.json."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cg.anytime import recover_history
from validation.ev_solution import validate_json_schedule
from config.model_formulation import completion_rows


def recovered_record(dest, data, input_sha, budget, method, seed, status, error=None):
    history = recover_history(dest.with_suffix(".incumbents.jsonl"), budget,
        lambda schedule, objective: validate_json_schedule(data, schedule, objective),
        expected_sha=input_sha)
    last = history[-1] if history else None
    return dict(status=status, termination_reason=status, error=error,
        method=method, seed=seed, instance_sha256=input_sha,
        objective=last["objective"] if last else None,
        schedule_makespan=last["objective"] if last else None,
        validation_passed=bool(last), has_feasible_solution=bool(last),
        time_to_first_feasible=history[0]["elapsed_seconds"] if last else None,
        best_found_seconds=last["elapsed_seconds"] if last else None,
        incumbent_history=history, trajectory_file=str(dest.with_suffix(".incumbents.jsonl")),
        validated_schedule=dict(schedule=last["schedule"]) if last else None)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--instance", action="append", default=[])
    p.add_argument("--instance-list", help="JSON manifest produced by prepare_scale")
    p.add_argument("--exact-repeats", type=int, help="Default: min(3, number of seeds)")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--limit", type=float, default=30)
    p.add_argument("--variant-file", help="JSON list of {name, env} variants")
    p.add_argument("--qaia-config", help="Append a qaia_tuned variant from frozen Optuna JSON")
    p.add_argument("--include-cim", action="store_true", help="Append a real CIM variant")
    p.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    args = p.parse_args()
    if not args.seeds or min(args.seeds) < 0 or len(set(args.seeds)) != len(args.seeds):
        p.error("seeds must be distinct nonnegative integers")
    if args.instance_list:
        args.instance.extend(json.loads(Path(args.instance_list).read_text(
            encoding="utf-8-sig"))["instances"])
    if not args.instance:
        p.error("provide --instance or --instance-list")
    exact_repeats = min(3, len(args.seeds)) if args.exact_repeats is None else args.exact_repeats
    if not 1 <= exact_repeats <= len(args.seeds):
        p.error("exact-repeats must be between 1 and the number of seeds")
    managed = {"QAIA_EXACT_MODE", "QAIA_PROVIDER", "QAIA_MAX_STREAK", "QAIA_N_ITER",
               "QAIA_BATCH_SIZE", "QAIA_MAX_COLUMNS", "QAIA_DT", "QAIA_XI", "QAIA_COLUMN_POLICY"}
    variants = json.loads((ROOT / "config/anytime.json").read_text(encoding="utf-8"))
    if args.variant_file:
        variants = json.loads(Path(args.variant_file).read_text(encoding="utf-8-sig"))
    frozen_metadata = None
    if args.qaia_config:
        from config.qaia_runtime import load_frozen
        frozen_env, frozen_metadata = load_frozen(args.qaia_config)
        variants.append(dict(name="qaia_tuned", env=frozen_env))
    if args.include_cim:
        variants.append(dict(name="cim", env=dict(QAIA_PROVIDER="cim",
            QAIA_EXACT_MODE="on_qaia_failure", QAIA_COLUMN_POLICY="combined")))
    if not isinstance(variants, list) or not variants:
        p.error("variant-file must contain a nonempty list")
    names = set()
    for item in variants:
        if not isinstance(item, dict):
            p.error("variant must be an object")
        name, env = item.get("name"), item.get("env")
        if (not isinstance(name, str) or not name or name in names
                or not all(c.isascii() and (c.isalnum() or c == "_") for c in name)
                or name in {"compact", "exact"}):
            p.error("variant names must be unique ASCII letters/digits/underscores")
        if not isinstance(env, dict) or set(env) - managed:
            p.error("unknown variant environment option")
        if any(not isinstance(value, str) for value in env.values()):
            p.error("environment values must be strings")
        names.add(name)
    if not math.isfinite(args.limit) or args.limit <= 0:
        p.error("limit must be positive and finite")
    paths = [(ROOT / x).resolve() for x in args.instance]
    if not all(x.is_file() for x in paths) or len({x.stem for x in paths}) != len(paths):
        p.error("instances must exist and have distinct filenames")
    out = Path(args.out_dir).resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = []
    fingerprints = set()
    plan = [("compact", None, 0, "compact", {})]
    for repeat, seed in enumerate(args.seeds):
        pair = [(item["env"].get("QAIA_PROVIDER", "qaia")+"_root", item["name"], seed, f"{item['name']}_s{seed}", item["env"])
                for item in variants]
        if repeat < exact_repeats:
            primal_seed = seed if os.getenv("BPC_PRIMAL_COMPLETION", "0") == "1" else 0
            pair.append(("exact", None, primal_seed, f"exact_r{repeat}", {}))
        if repeat % 2:
            pair.reverse()
        plan.extend(pair)
    (out / "manifest.json").write_text(json.dumps(dict(
        variants=variants, seeds=args.seeds, limit=args.limit, exact_repeats=exact_repeats,
        timing_basis="bp_active_excluding_cloud_call",
        offline_tuning=frozen_metadata,
        cim_environment={key: os.getenv(key) for key in (
            "CIM_DEVICE_ID", "CIM_MAX_BITS", "CIM_PRECISION", "CIM_MAX_CALLS",
            "CIM_CACHE_DIR")},
        completion_rows=completion_rows(),
        capacity_bound_environment={key: os.getenv(key, default) for key, default in (
            ("BPC_CAPACITY_BOUND", "1"), ("BPC_BOUND_LP_SECONDS", "2"))},
        primal_completion_environment={key: os.getenv(key, default) for key, default in (
            ("BPC_PRIMAL_COMPLETION", "0"), ("BPC_PRIMAL_ATTEMPTS", "20"),
            ("BPC_PRIMAL_SECONDS", "2"))},
        exact_pool_search_mode=os.getenv("EXACT_POOL_SEARCH_MODE", "2"),
        restricted_mip_environment={key: os.getenv(key, default) for key, default in (
            ("BPC_RMP_MIP", "1"), ("BPC_RMP_MIP_EVERY", "20"),
            ("BPC_RMP_MIP_SECONDS", "0.5"), ("BPC_RMP_MIP_FRACTION", "0.1"))},
        instances=[str(x) for x in paths]), indent=2), encoding="utf-8")
    for path in paths:
        reference = None
        runs = []
        raw = path.read_bytes()
        input_sha = hashlib.sha256(raw).hexdigest()
        data = json.loads(raw)
        for method, policy, seed, label, overrides in plan:
            dest = out / f"{path.stem}_{label}.json"
            env = {k: v for k, v in os.environ.items() if k not in managed}
            env.update(BPC_VERBOSE="0", BPC_DUMP_LP="0", QAIA_COLUMN_POLICY="combined")
            env.update(overrides)
            command = [sys.executable, str(ROOT / "experiments/run_instance.py"),
                       "--instance", str(path), "--method", method,
                       "--seed", str(seed), "--limit", str(args.limit), "--out", str(dest)]
            if policy == "qaia_tuned" and args.qaia_config:
                command.extend(["--qaia-config", str(Path(args.qaia_config).resolve())])
            start = time.perf_counter()
            record = {}
            print(path.stem, label, "running (CIM waits for cloud return)" if method == "cim_root"
                  else "running", flush=True)
            with dest.with_suffix(".process.log").open("x", encoding="utf-8") as log:
                try:
                    proc = subprocess.run(command, cwd=ROOT, env=env, stdout=log,
                                          stderr=subprocess.STDOUT,
                                          timeout=None if method == "cim_root" else args.limit+60)
                    record = json.loads(dest.read_text(encoding="utf-8")) if dest.exists() else {}
                    if proc.returncode != 0 or not record:
                        record = recovered_record(dest, data, input_sha, args.limit, method, seed,
                                                  "error", "process failed or result missing")
                except subprocess.TimeoutExpired:
                    try:
                        record = recovered_record(dest, data, input_sha, args.limit,
                                                  method, seed, "external_timeout")
                    except (ValueError, OSError) as exc:
                        record = dict(status="error", error=f"trajectory recovery failed: {exc}")
                except (ValueError, OSError) as exc:
                    record = dict(status="error", error=str(exc))
            if record.get("instance_sha256") not in (None, input_sha):
                record.update(status="error", validation_passed=False,
                              has_feasible_solution=False, error="input changed during batch")
            if not dest.exists() or record.get("status") in {"external_timeout", "error"}:
                dest.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            fp = record.get("source_sha256")
            if fp:
                fingerprints.add(fp)
                if len(fingerprints) > 1:
                    raise RuntimeError("Source changed during diagnostic batch")
            if method == "compact" and record.get("status") == "optimal" and record.get("validation_passed"):
                reference = record
            check = "not_certified"
            if record.get("status") == "optimal":
                if not record.get("validation_passed"):
                    check = "invalid_schedule"
                elif reference is None:
                    check = "reference_not_certified"
                elif record.get("instance_sha256") != reference.get("instance_sha256"):
                    check = "input_changed"
                elif record.get("objective") is None or abs(record["objective"]-reference["objective"]) > 1e-6:
                    check = "objective_mismatch"
                else:
                    check = "matched_reference"
            entry = dict(method=method, policy=policy,
                         seed=seed, result=dest.name, status=record.get("status", "error"),
                         check=check, objective=record.get("objective"),
                         feasible_makespan=record.get("schedule_makespan"),
                         validation_passed=record.get("validation_passed", False),
                         statistics=record.get("statistics"), error=record.get("error"),
                         has_feasible_solution=record.get("has_feasible_solution", False),
                         time_to_first_feasible=record.get("time_to_first_feasible"),
                         best_found_seconds=record.get("best_found_seconds"),
                         budget_snapshots=record.get("budget_snapshots"),
                         trajectory_file=record.get("trajectory_file"),
                         wall_seconds=record.get("wall_seconds"),
                         solve_seconds=record.get("solve_seconds"),
                         cloud_excluded_seconds=record.get("cloud_excluded_seconds"),
                         timing_basis=record.get("timing_basis"),
                         process_seconds=time.perf_counter()-start)
            runs.append(entry)
            print(path.stem, label, entry["status"], check, flush=True)
            # Incremental checkpoint preserves every attempted run, even when interrupted.
            (out / f"{path.stem}_diagnostic.json").write_text(
                json.dumps(runs, ensure_ascii=False, indent=2), encoding="utf-8")
        groups = {}
        for key in ["compact", "exact", *[item["name"] for item in variants]]:
            group = [r for r in runs if (r["policy"] or r["method"]) == key]
            good = [r for r in group if r["check"] == "matched_reference"]
            roots = [(r.get("statistics") or {}).get("root_diagnostics") or {} for r in group]
            root_times = [r["pricing_seconds"] for r in roots if r.get("cg_certified")]
            feasible = [r["feasible_makespan"] for r in group
                        if r["validation_passed"] and r.get("feasible_makespan") is not None]
            groups[key] = dict(
                attempted=len(group),
                optimal_count=sum(r["status"] == "optimal" and r["validation_passed"] for r in group),
                matched_reference_count=len(good),
                statuses={s: sum(r["status"] == s for r in group)
                          for s in sorted({r["status"] for r in group})},
                median_seconds=statistics.median(r["solve_seconds"] for r in group)
                    if group and all(r["status"] == "optimal" and r["validation_passed"]
                        and r["check"] not in {"objective_mismatch", "input_changed", "invalid_schedule"}
                        for r in group) else None,
                feasible_count=len(feasible),
                feasible_rate=len(feasible)/len(group) if group else None,
                all_feasible_makespans=[r["feasible_makespan"] if r["validation_passed"] else None for r in group],
                first_feasible_seconds=[r["time_to_first_feasible"] for r in group],
                median_feasible_makespan=statistics.median(feasible) if feasible else None,
                median_all_runs_makespan=statistics.median(feasible)
                    if feasible and len(feasible) == len(group) else None,
                root_certified=len(root_times),
                median_root_pricing_seconds=statistics.median(root_times)
                    if len(root_times) == len(group) and group else None)
        report.append(dict(schema_version="anytime-summary-v2", instance=str(path),
                           timing_basis="bp_active_excluding_cloud_call",
                           limit=args.limit, completion_rows=completion_rows(), groups=groups))
        (out / "diagnostic_summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Collection finished. Compare feasible_rate and objectives first; timeouts are retained.")


if __name__ == "__main__":
    main()
