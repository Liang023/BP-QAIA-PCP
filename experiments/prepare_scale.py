"""Generate a fixed scale grid and a manifest for run_batch (no solver-based selection)."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ev.generate_ev_instances_v1 import build_instance
from experiments.run_instance import check_input


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--family", choices=["acn", "synthetic"], required=True)
    p.add_argument("--sizes", type=int, nargs="+", required=True)
    p.add_argument("--ratios", type=int, nargs="+", default=[4], help="Vehicles per charger")
    p.add_argument("--dates", nargs="+", default=[])
    p.add_argument("--data-seeds", type=int, nargs="+", default=[10])
    p.add_argument("--raw", default="data/raw/acn/caltech_sessions.json")
    p.add_argument("--max-vertices", type=int, default=3000)
    p.add_argument("--slot-minutes", type=int, default=15)
    p.add_argument("--power-kw", default="7")
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()
    if args.family == "acn" and not args.dates:
        p.error("ACN requires --dates")
    if any(n <= 0 or r <= 0 or n % r for n in args.sizes for r in args.ratios):
        p.error("Each size must be a positive multiple of each ratio")
    out = ROOT / args.out_dir
    out.mkdir(parents=True, exist_ok=False)
    manifest = dict(design=vars(args), instances=[], dimensions=[])
    samples = args.dates if args.family == "acn" else args.data_seeds
    for sample in samples:
        for n in args.sizes:
            for ratio in args.ratios:
                chargers = n // ratio
                stem = (f"{sample}_N{n}_C{chargers}" if args.family == "acn"
                        else f"v1_N{n}_C{chargers}_s{sample}")
                path = out / f"{stem}.json"
                if args.family == "acn":
                    subprocess.run([sys.executable, str(ROOT / "ev/acn_to_ev.py"),
                        "--raw", str(ROOT / args.raw), "--date", sample,
                        "--max-sessions", str(n), "--chargers", str(chargers),
                        "--slot-minutes", str(args.slot_minutes), "--power-kw", args.power_kw,
                        "--max-vertices", str(args.max_vertices), "--out", str(path)],
                        cwd=ROOT, check=True)
                    data = json.loads(path.read_text(encoding="utf-8"))
                else:
                    # Hold windows fixed across charger counts; plant at the tightest capacity.
                    base_chargers = n // max(args.ratios)
                    data = build_instance(n, base_chargers, sample)
                    data.update(name=stem, num_chargers=chargers,
                                metadata=dict(generation_chargers=base_chargers))
                    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                check_input(data)
                vertices = sum(len(v["candidates"]) for v in data["vehicles"])
                if data["num_vehicles"] != n or vertices > args.max_vertices:
                    raise ValueError(f"{path}: actual N={data['num_vehicles']}, V={vertices}; inspect data/audit")
                manifest["instances"].append(str(path.resolve()))
                manifest["dimensions"].append(dict(name=stem, vehicles=n, chargers=chargers,
                    vertices=vertices, instance_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    target = out / "instances.json"
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Manifest: {target}; instances: {len(manifest['instances'])}")


if __name__ == "__main__":
    main()
