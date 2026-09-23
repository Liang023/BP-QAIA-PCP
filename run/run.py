"""Run the frozen Exact / QAIA / CIM comparison and export its reports.

From the repository root: python -m run.run --out-dir results/competition_three_600_final
"""

import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime


ROOT = Path(__file__).resolve().parents[1]
ECLOUD_ACCESS_KEY = "fdb23479787a49d99105b4cc7d996c5b"
ECLOUD_SECRET_KEY = "1d257e702c564b51b1cb09b4f507eb8e"


def main():
    os.chdir(ROOT)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-list", default="data/acn_competition_0930_v2/instances.json")
    parser.add_argument("--qaia-config", default="tuning/acn_train_v1/best_qaia.json")
    parser.add_argument("--out-dir", default="results/capacity_bound_"+datetime.now().strftime("%Y%m%d_%H%M%S"),
                        help="New result directory; a timestamp is used by default")
    parser.add_argument("--limit", type=int, default=1200)
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--cim-call-seconds", type=int, default=300)
    parser.add_argument("--all-instances", action="store_true", help="Run all 12 instead of the first six")
    parser.add_argument("--dates", nargs="+", default=["2019-03-11", "2019-03-12"])
    parser.add_argument("--capacity-bound", choices=["0", "1"], default="1")
    parser.add_argument("--bound-lp-seconds", type=float, default=2.0)
    args = parser.parse_args()

    if Path(args.out_dir).exists():
        parser.error("out-dir already exists; the batch runner cannot resume or overwrite runs")
    env = os.environ.copy()
    env.update(
        EXACT_POOL_SEARCH_MODE="0",
        BPC_COMPLETION_ROWS="vehicle",
        BPC_RMP_MIP="1",
        BPC_RMP_MIP_EVERY="20",
        BPC_RMP_MIP_SECONDS="0.5",
        BPC_RMP_MIP_FRACTION="0.1",
        BPC_PRIMAL_COMPLETION="0",
        BPC_CAPACITY_BOUND=args.capacity_bound,
        BPC_BOUND_LP_SECONDS=str(args.bound_lp_seconds),
        CIM_DEVICE_ID="WuYue-QPU-Qboson-1000",
        CIM_MAX_BITS="1000",
        CIM_PRECISION="8",
        CIM_MAX_CALLS="1",
        CIM_CALL_SECONDS=str(args.cim_call_seconds),
        ECLOUD_ACCESS_KEY=ECLOUD_ACCESS_KEY,
        ECLOUD_SECRET_KEY=ECLOUD_SECRET_KEY,
    )

    instances = json.loads((ROOT / args.instance_list).read_text(encoding="utf-8-sig"))["instances"]
    if not args.all_instances:
        instances = [p for p in instances if Path(p.replace("\\", "/")).name.startswith(
            tuple(day+"_" for day in args.dates))]
    # Manifests created on another computer may contain obsolete absolute paths.
    manifest_dir = (ROOT / args.instance_list).parent
    instances = [str((manifest_dir / Path(p.replace("\\", "/")).name).resolve())
                 if not Path(p).is_file() else p for p in instances]
    if not instances:
        parser.error("no instances selected from the manifest")

    out = Path(args.out_dir)
    summary = out.with_name(out.name + "_summary")
    anytime = out.with_name(out.name + "_anytime")
    commands = [
        [sys.executable, "-m", "experiments.run_batch",
         *(arg for path in instances for arg in ("--instance", path)),
         "--variant-file", "config/cim_only.json",
         "--qaia-config", args.qaia_config,
         "--seeds", *map(str, args.seeds),
         "--exact-repeats", str(len(args.seeds)),
         "--limit", str(args.limit), "--out-dir", str(out)],
        [sys.executable, "-m", "experiments.summarize_scale",
         "--results-dir", str(out), "--out-dir", str(summary)],
        [sys.executable, "-m", "experiments.compare_anytime",
         "--results-dir", str(out),
         "--checkpoints", *map(str, (30, 120, args.limit)),
         "--out-dir", str(anytime)],
    ]
    print(json.dumps(dict(online_limit_seconds=args.limit,
        cim_call_seconds=args.cim_call_seconds, instances=instances,
        seeds=args.seeds, results=str(out), summary=str(summary), anytime=str(anytime)),
        ensure_ascii=False, indent=2), flush=True)
    for command in commands:
        subprocess.run(command, cwd=ROOT, env=env, check=True)
    # One wide, Excel-friendly CSV: one row per instance and algorithm repeat.
    with (summary / "runs.csv").open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        with (out / "results.csv").open("w", encoding="utf-8-sig", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows(reader)
    print(f"Combined CSV: {out / 'results.csv'}", flush=True)


if __name__ == "__main__":
    main()
