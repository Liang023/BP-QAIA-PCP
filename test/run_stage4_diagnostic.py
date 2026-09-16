"""Collect all planned outcomes, including timeouts; never write PASS.json."""
import argparse
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--instance", action="append", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--limit", type=float, default=30)
    p.add_argument("--variant-file", help="JSON list of {name, env} variants")
    p.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    args = p.parse_args()
    if not args.seeds or min(args.seeds) < 0 or len(set(args.seeds)) != len(args.seeds):
        p.error("seeds must be distinct nonnegative integers")
    managed = {"QAIA_EXACT_MODE", "QAIA_PROVIDER", "QAIA_MAX_STREAK", "QAIA_N_ITER",
               "QAIA_BATCH_SIZE", "QAIA_MAX_COLUMNS", "QAIA_DT", "QAIA_COLUMN_POLICY"}
    variants = [dict(name=x, env={"QAIA_COLUMN_POLICY": x})
                for x in ("combined", "warm_start_only")]
    if args.variant_file:
        variants = json.loads(Path(args.variant_file).read_text(encoding="utf-8-sig"))
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
        pair = [("qaia_root", item["name"], seed, f"{item['name']}_s{seed}", item["env"])
                for item in variants]
        if repeat < 3:
            pair.append(("exact", None, 0, f"exact_r{repeat}", {}))
        if repeat % 2:
            pair.reverse()
        plan.extend(pair)
    (out / "manifest.json").write_text(json.dumps(dict(
        variants=variants, seeds=args.seeds, limit=args.limit,
        exact_pool_search_mode=os.getenv("EXACT_POOL_SEARCH_MODE", "2"),
        instances=[str(x) for x in paths]), indent=2), encoding="utf-8")
    for path in paths:
        reference = None
        runs = []
        for method, policy, seed, label, overrides in plan:
            dest = out / f"{path.stem}_{label}.json"
            env = {k: v for k, v in os.environ.items() if k not in managed}
            env.update(BPC_VERBOSE="0", BPC_DUMP_LP="0", QAIA_COLUMN_POLICY="combined")
            env.update(overrides)
            command = [sys.executable, str(ROOT / "test/run_stage1.py"),
                       "--instance", str(path), "--method", method,
                       "--seed", str(seed), "--limit", str(args.limit), "--out", str(dest)]
            start = time.perf_counter()
            record = {}
            with dest.with_suffix(".process.log").open("x", encoding="utf-8") as log:
                try:
                    proc = subprocess.run(command, cwd=ROOT, env=env, stdout=log,
                                          stderr=subprocess.STDOUT, timeout=args.limit+60)
                    record = json.loads(dest.read_text(encoding="utf-8")) if dest.exists() else {}
                    if proc.returncode != 0 or not record:
                        record.update(status="error", error="process failed or result missing")
                except subprocess.TimeoutExpired:
                    record = dict(status="external_timeout", objective=None)
                except (ValueError, OSError) as exc:
                    record = dict(status="error", error=str(exc))
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
            entry = dict(method=method, policy=policy if method == "qaia_root" else None,
                         seed=seed, result=dest.name, status=record.get("status", "error"),
                         check=check, objective=record.get("objective"),
                         feasible_makespan=record.get("schedule_makespan"),
                         validation_passed=record.get("validation_passed", False),
                         statistics=record.get("statistics"), error=record.get("error"),
                         wall_seconds=record.get("wall_seconds"),
                         process_seconds=time.perf_counter()-start)
            runs.append(entry)
            print(path.stem, label, entry["status"], check, flush=True)
            # Incremental checkpoint preserves every attempted run, even when interrupted.
            (out / f"{path.stem}_diagnostic.json").write_text(
                json.dumps(runs, ensure_ascii=False, indent=2), encoding="utf-8")
        groups = {}
        for key in ["exact", *[item["name"] for item in variants]]:
            group = [r for r in runs if (r["policy"] or r["method"]) == key]
            good = [r for r in group if r["check"] == "matched_reference"]
            roots = [(r.get("statistics") or {}).get("root_diagnostics") or {} for r in group]
            root_times = [r["pricing_seconds"] for r in roots if r.get("cg_certified")]
            feasible = [r["feasible_makespan"] for r in group
                        if r["validation_passed"] and r.get("feasible_makespan") is not None]
            groups[key] = dict(
                attempted=len(group), certified=len(good),
                statuses={s: sum(r["status"] == s for r in group)
                          for s in sorted({r["status"] for r in group})},
                median_seconds=statistics.median(r["wall_seconds"] for r in good)
                    if len(good) == len(group) and good else None,
                feasible_count=len(feasible),
                median_feasible_makespan=statistics.median(feasible) if feasible else None,
                root_certified=len(root_times),
                median_root_pricing_seconds=statistics.median(root_times)
                    if len(root_times) == len(group) and group else None)
        report.append(dict(instance=str(path), limit=args.limit, groups=groups))
        (out / "diagnostic_summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Diagnostic collection finished. This is NOT a PASS certificate.")


if __name__ == "__main__":
    main()