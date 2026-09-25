"""Run the Exact / QAIA / CIM comparison with bounded incumbent repair.

From the repository root: python -m run.run --out-dir results/primal_v3_selected
"""

import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
ECLOUD_ACCESS_KEY = "fdb23479787a49d99105b4cc7d996c5b"
ECLOUD_SECRET_KEY = "1d257e702c564b51b1cb09b4f507eb8e"


def main():
    os.chdir(ROOT)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-list", default="data/instances/instances.json")
    parser.add_argument("--qaia-config", default="config/qaia_candidates_v3.json")
    parser.add_argument("--out-dir", default="results/result_c5",
                        help="Persistent result directory; completed runs are skipped")
    parser.add_argument("--limit", type=int, default=1800,
                        help="BP seconds excluding blocking CIM cloud calls")
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2], help="Random seeds for each instance")
    parser.add_argument("--exact-repeats", type=int, default=None,
                        help="Default: one Exact repeat per seed")
    parser.add_argument("--primal-completion", choices=["0", "1"], default="1",
                        help="Enable the same root repair for Exact, QAIA and CIM")
    parser.add_argument("--primal-injection", choices=["best", "all"], default="best")
    parser.add_argument("--neighborhood", choices=["0", "1"], default="1")
    parser.add_argument("--neighborhood-seconds", type=float, default=2.0)
    parser.add_argument("--neighborhood-vehicles", type=int, default=4)
    parser.add_argument("--neighborhood-interval", type=float, default=30.0)
    parser.add_argument("--neighborhood-fraction", type=float, default=0.05)
    parser.add_argument("--variant-file", default="config/cim_only.json")
    parser.add_argument("--all-instances", action="store_true", help="Ignore a --dates filter")
    parser.add_argument("--dates", nargs="+", help="Optional date subset of the selected manifest")
    parser.add_argument("--capacity-bound", choices=["0", "1"], default="1")
    parser.add_argument("--bound-lp-seconds", type=float, default=2.0)
    args = parser.parse_args()

    if args.exact_repeats is None:
        args.exact_repeats = len(args.seeds)
    env = os.environ.copy()
    env.update(
        EXACT_POOL_SEARCH_MODE="0",
        BPC_COMPLETION_ROWS="vehicle",
        BPC_RMP_MIP="1",
        BPC_RMP_MIP_EVERY="20",
        BPC_RMP_MIP_SECONDS="0.5",
        BPC_RMP_MIP_FRACTION="0.1",
        BPC_PRIMAL_COMPLETION=args.primal_completion,
        BPC_PRIMAL_ATTEMPTS="20",
        BPC_PRIMAL_SECONDS="2",
        BPC_PRIMAL_INJECTION=args.primal_injection,
        BPC_NEIGHBORHOOD=args.neighborhood,
        BPC_NEIGHBORHOOD_SECONDS=str(args.neighborhood_seconds),
        BPC_NEIGHBORHOOD_VEHICLES=str(args.neighborhood_vehicles),
        BPC_NEIGHBORHOOD_INTERVAL=str(args.neighborhood_interval),
        BPC_NEIGHBORHOOD_COOLDOWN="10",
        BPC_NEIGHBORHOOD_FRACTION=str(args.neighborhood_fraction),
        BPC_CAPACITY_BOUND=args.capacity_bound,
        BPC_BOUND_LP_SECONDS=str(args.bound_lp_seconds),
        CIM_DEVICE_ID="WuYue-QPU-Qboson-1000",
        CIM_MAX_BITS="1000",
        CIM_PRECISION="8",
        CIM_MAX_CALLS="3",
        ECLOUD_ACCESS_KEY=ECLOUD_ACCESS_KEY,
        ECLOUD_SECRET_KEY=ECLOUD_SECRET_KEY,
    )

    instances = json.loads((ROOT / args.instance_list).read_text(encoding="utf-8-sig"))["instances"]
    if args.dates and not args.all_instances:
        instances = [p for p in instances if Path(p.replace("\\", "/")).name.startswith(
            tuple(day+"_" for day in args.dates))]
    # Manifests created on another computer may contain obsolete absolute paths.
    manifest_dir = (ROOT / args.instance_list).parent
    instances = [str((manifest_dir / Path(p.replace("\\", "/")).name).resolve())
                 if not Path(p).is_file() else p for p in instances]
    if not instances:
        parser.error("no instances selected from the manifest")

    out = Path(args.out_dir)
    summary = out / "summary"
    anytime = out / "anytime"
    commands = [
        [sys.executable, "-m", "experiments.run_batch",
         *(arg for path in instances for arg in ("--instance", path)),
         "--variant-file", args.variant_file,
         "--qaia-config", args.qaia_config,
         "--seeds", *map(str, args.seeds),
         "--exact-repeats", str(args.exact_repeats),
         "--limit", str(args.limit), "--out-dir", str(out)],
        [sys.executable, "-m", "experiments.summarize_scale",
         "--results-dir", str(out), "--out-dir", str(summary)],
        [sys.executable, "-m", "experiments.compare_anytime",
         "--results-dir", str(out),
         "--checkpoints", *map(str, (10, 30, 120, args.limit)),
         "--out-dir", str(anytime)],
    ]
    print(json.dumps(dict(bp_limit_seconds=args.limit,
        timing_basis="bp_active_excluding_cloud_call", cim_wait_timeout=None, instances=instances,
        seeds=args.seeds, exact_repeats=args.exact_repeats,
        neighborhood=args.neighborhood, primal_injection=args.primal_injection, results=str(out), summary=str(summary), anytime=str(anytime)),
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

