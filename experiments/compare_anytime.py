"""Compare validated solution quality at fixed time checkpoints.

Input is an unmodified experiments.run_batch directory. This script only reads files.
"""
import argparse
import csv
import json
from pathlib import Path
from statistics import median


def best_at(record, seconds):
    if not (record.get("validation_passed") and record.get("has_feasible_solution")):
        return None
    values = [event["objective"] for event in record.get("incumbent_history", [])
              if event["elapsed_seconds"] <= seconds + 1e-9]
    return min(values) if values else None


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def compare(folder, requested):
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    limit = float(manifest["limit"])
    checkpoints = sorted({float(t) for t in requested if 0 < t <= limit} | {limit})
    seeds = manifest["seeds"]
    repeats = manifest.get("exact_repeats", min(3, len(seeds)))
    aggregates, pairs, pair_summaries = [], [], []
    for instance in manifest["instances"]:
        name = instance.replace("\\", "/").rsplit("/", 1)[-1].removesuffix(".json")
        entries = json.loads((folder / f"{name}_diagnostic.json").read_text(encoding="utf-8"))
        expected = 1 + repeats + len(seeds) * len(manifest["variants"])
        if len(entries) != expected:
            raise ValueError(f"{name}: {len(entries)} runs, expected {expected}")
        groups = {}
        hashes = set()
        for entry in entries:
            record = json.loads((folder / entry["result"]).read_text(encoding="utf-8"))
            method = entry.get("policy") or entry["method"]
            groups.setdefault(method, []).append((entry, record))
            if record.get("source_sha256"):
                hashes.add(record["source_sha256"])
        if len(hashes) > 1:
            raise ValueError(f"{name}: runs have different source hashes")
        exact = {int(entry["result"].rsplit("_exact_r", 1)[1].removesuffix(".json")): record
                 for entry, record in groups["exact"]}
        reference = next((record["objective"] for _, record in groups["compact"]
                          if record["status"] == "optimal" and record.get("validation_passed")), None)
        common = dict(batch=folder.name, instance=name, budget=limit,
                      timing_basis=manifest.get("timing_basis", "wall"),
                      completion_rows=manifest.get("completion_rows", "vertex"))
        for t in checkpoints:
            for method, group in groups.items():
                values = [best_at(record, t) for _, record in group]
                feasible = [value for value in values if value is not None]
                aggregates.append(dict(**common, checkpoint=t, method=method,
                    runs=len(group), feasible=len(feasible), feasible_rate=len(feasible)/len(group),
                    median_all=median(feasible) if len(feasible) == len(group) else None,
                    median_conditional=median(feasible) if feasible else None,
                    reference_optimum=reference))
            for method, group in groups.items():
                if method in ("compact", "exact"):
                    continue
                by_seed = {entry["seed"]: record for entry, record in group}
                outcomes = []
                for index, seed in enumerate(seeds):
                    # Exact is deterministic in the final configuration. When
                    # run once, compare every heuristic seed with that baseline.
                    repeat = index if index < repeats else 0
                    value = best_at(by_seed[seed], t)
                    baseline = best_at(exact[repeat], t)
                    outcome = ("both_missing" if value is None and baseline is None else
                               "method_only" if baseline is None else
                               "exact_only" if value is None else
                               "method" if value < baseline else
                               "exact" if value > baseline else "tie")
                    row = dict(**common, checkpoint=t, method=method, seed=seed,
                        exact_repeat=repeat, method_objective=value, exact_objective=baseline,
                        exact_reference_reused=len(seeds) > repeats,
                        delta_vs_exact=value - baseline
                            if value is not None and baseline is not None else None,
                        outcome=outcome)
                    pairs.append(row)
                    outcomes.append(row)
                deltas = [row["delta_vs_exact"] for row in outcomes
                          if row["delta_vs_exact"] is not None]
                pair_summaries.append(dict(**common, checkpoint=t, method=method,
                    pairs=len(outcomes), both_feasible=len(deltas),
                    method_wins=sum(row["outcome"] == "method" for row in outcomes),
                    exact_wins=sum(row["outcome"] == "exact" for row in outcomes),
                    ties=sum(row["outcome"] == "tie" for row in outcomes),
                    method_only=sum(row["outcome"] == "method_only" for row in outcomes),
                    exact_only=sum(row["outcome"] == "exact_only" for row in outcomes),
                    both_missing=sum(row["outcome"] == "both_missing" for row in outcomes),
                    median_delta_complete=median(deltas) if len(deltas) == len(outcomes) else None))
    return aggregates, pairs, pair_summaries


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results-dir", action="append", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--checkpoints", type=float, nargs="+", default=[1, 10, 30, 60, 120, 300])
    args = p.parse_args()
    if any(t <= 0 for t in args.checkpoints):
        p.error("checkpoints must be positive")
    tables = [[], [], []]
    for folder in args.results_dir:
        for combined, rows in zip(tables, compare(Path(folder), args.checkpoints)):
            combined.extend(rows)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=False)
    for filename, rows in zip(("checkpoints.csv", "paired.csv", "paired_summary.csv"), tables):
        write_csv(out / filename, rows)
    print(f"Wrote {out}; paired records: {len(tables[1])}")


if __name__ == "__main__":
    main()
