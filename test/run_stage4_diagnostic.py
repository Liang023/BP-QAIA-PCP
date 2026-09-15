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
    args = p.parse_args()
    if not math.isfinite(args.limit) or args.limit <= 0:
        p.error("limit must be positive and finite")
    paths = [(ROOT / x).resolve() for x in args.instance]
    if not all(x.is_file() for x in paths) or len({x.stem for x in paths}) != len(paths):
        p.error("instances must exist and have distinct filenames")
    out = Path(args.out_dir).resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = []
    fingerprints = set()
    # 1 compact + 3 exact + 5 combined + 5 warm_start_only per instance.
    plan = [("compact", "combined", 0, "compact")]
    for seed in range(5):
        pair = [("qaia_root", policy, seed, f"{policy}_s{seed}")
                for policy in ("combined", "warm_start_only")]
        if seed % 2:
            pair.reverse()
        if seed < 3:
            pair.insert(0, ("exact", "combined", 0, f"exact_r{seed}"))
        plan.extend(pair)
    for path in paths:
        reference = None
        runs = []
        for method, policy, seed, label in plan:
            dest = out / f"{path.stem}_{label}.json"
            env = dict(os.environ, BPC_VERBOSE="0", BPC_DUMP_LP="0",
                       QAIA_COLUMN_POLICY=policy)
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
        for key in ("exact", "combined", "warm_start_only"):
            group = [r for r in runs if (r["policy"] or r["method"]) == key]
            good = [r for r in group if r["check"] == "matched_reference"]
            groups[key] = dict(attempted=len(group), certified=len(good),
                               median_seconds=statistics.median(r["wall_seconds"] for r in good)
                               if len(good) == len(group) and good else None)
        report.append(dict(instance=str(path), limit=args.limit, groups=groups))
        (out / "diagnostic_summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Diagnostic collection finished. This is NOT a PASS certificate.")


if __name__ == "__main__":
    main()