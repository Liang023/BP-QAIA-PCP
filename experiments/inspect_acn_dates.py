"""Audit calendar dates with the existing converter, without any optimization.

Stores full daily converted instances and audits. Large requested N is only to
count all eligible sessions; it does not change the converter's filtering rules.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw", required=True)
    p.add_argument("--split-file", default="config/acn_final_split.json")
    p.add_argument("--split", choices=["train", "validation", "test", "external_test"], required=True)
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()
    design = json.loads(Path(args.split_file).read_text(encoding="utf-8"))
    out = Path(args.out_dir).resolve()
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    for day in design[args.split]:
        target = out/f"{day}.json"
        proc = subprocess.run([sys.executable, "-m", "ev.acn_to_ev", "--raw", str(Path(args.raw).resolve()),
            "--date", day, "--max-sessions", "1000000", "--max-vertices", "1000000000",
            "--chargers", "1", "--slot-minutes", str(design["slot_minutes"]),
            "--power-kw", str(design["power_kw"]), "--out", str(target)], cwd=ROOT,
            capture_output=True, text=True)
        audit = target.with_suffix(".audit.json")
        if not audit.exists():
            raise RuntimeError(f"Converter failed before audit for {day}: {proc.stderr}")
        report = json.loads(audit.read_text(encoding="utf-8"))
        row = dict(date=day, eligible=report["eligible_sessions"], status=report["status"],
                   reason=report["reason"], counts=report["counts"], sizes=[])
        if target.exists():
            vehicles = json.loads(target.read_text(encoding="utf-8"))["vehicles"]
            for n in design["sizes"]:
                if len(vehicles) >= n:
                    count = sum(len(v["candidates"]) for v in vehicles[:n])
                    row["sizes"].append(dict(n=n, vertices=count,
                        cim_1000_raw_size_fits=count+1 <= 1000))
        rows.append(row)
        print(day, "eligible:", row["eligible"], "sizes:", row["sizes"])
    (out/"inventory.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
