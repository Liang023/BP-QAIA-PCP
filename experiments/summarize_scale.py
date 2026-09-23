"""Export validated anytime results; missing solutions stay empty, never become penalties."""
import argparse
import csv
import json
from pathlib import Path
from statistics import median


def write_csv(path, rows):
    if rows:
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def collect(folder):
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    formulation = manifest.get("completion_rows", "vertex")
    runs, trajectories, summaries, comparisons = [], [], [], []
    for instance in manifest["instances"]:
        # Windows paths in an archived manifest must also work on Linux.
        name = instance.replace("\\", "/").rsplit("/", 1)[-1].removesuffix(".json")
        entries = json.loads((folder / f"{name}_diagnostic.json").read_text(encoding="utf-8"))
        expected = 1 + len(manifest["seeds"]) * len(manifest["variants"]) + manifest.get(
            "exact_repeats", min(3, len(manifest["seeds"])))
        if len(entries) != expected:
            raise ValueError(f"{name}: incomplete batch ({len(entries)}/{expected})")
        records = [(e, json.loads((folder / e["result"]).read_text(encoding="utf-8"))) for e in entries]
        reference = next((r["objective"] for e, r in records if e["method"] == "compact"
            and r["status"] == "optimal" and r.get("validation_passed")), None)
        groups = {}
        for entry, record in records:
            method = entry.get("policy") or entry["method"]
            stats = record.get("statistics") or {}
            metrics = (stats.get("root_diagnostics") or {}).get("heuristic_metrics") or {}
            cim = metrics.get("cim") or {}
            feasible = bool(record.get("validation_passed") and record.get("has_feasible_solution"))
            objective = record.get("objective") if feasible else None
            lower_bound = stats.get("global_lower_bound")
            bp_gap_percent = (100 * (objective - lower_bound) / max(abs(objective), 1e-6)
                if objective is not None and lower_bound is not None else None)
            reference_gap_percent = (100 * (objective - reference) / max(abs(objective), 1e-6)
                if objective is not None and reference is not None else None)
            row = dict(batch=folder.name, instance=name, budget=manifest["limit"], method=method,
                completion_rows=formulation,
                result=entry["result"], seed=entry["seed"], status=record["status"],
                feasible=int(feasible), objective=objective, reference_optimum=reference,
                deviation_percent=(100 * (objective-reference)/reference
                    if objective is not None and reference is not None and reference > 0 else None),
                bp_lower_bound=lower_bound, bp_gap_percent=bp_gap_percent,
                reference_gap_percent=reference_gap_percent,
                first_feasible_seconds=record.get("time_to_first_feasible"),
                best_found_seconds=record.get("best_found_seconds"), wall_seconds=record.get("wall_seconds"),
                graph_seconds=record.get("graph_seconds"),
                root_initialization_seconds=stats.get("root_initialization_seconds"),
                node_setup_seconds=stats.get("node_setup_seconds"), branch_seconds=stats.get("branch_seconds"),
                pricing_seconds=stats.get("pricing_seconds"),
                nodes_processed=stats.get("nodes_processed"),
                root_lp=(stats.get("root_diagnostics") or {}).get("lp_objective"),
                root_cg_iterations=(stats.get("root_diagnostics") or {}).get("cg_iterations"),
                restricted_mip_seconds=stats.get("restricted_mip_seconds"),
                heuristic_provider=record.get("heuristic_provider"),
                cim_requests=cim.get("requests"), cim_completed=cim.get("completed"),
                cim_timeouts=cim.get("timeouts"), cim_size_skips=cim.get("size_skips"),
                cim_seconds=cim.get("seconds"),
                tuning_config_sha256=(record.get("offline_tuning") or {}).get("sha256"),
                source_sha256=record.get("source_sha256"), error=record.get("error"))
            runs.append(row)
            groups.setdefault(method, []).append(row)
            for event in record.get("incumbent_history", []):
                trajectories.append(dict(batch=folder.name, instance=name, budget=manifest["limit"],
                    completion_rows=formulation,
                    method=method, result=entry["result"], seed=entry["seed"],
                    seconds=event["elapsed_seconds"], objective=event["objective"], source=event["source"]))
        per_method = {}
        for method, group in groups.items():
            feasible = [r for r in group if r["feasible"]]
            errors = sum(r["status"] in ("error", "external_timeout") for r in group)
            row = dict(batch=folder.name, instance=name, budget=manifest["limit"], method=method,
                completion_rows=formulation,
                runs=len(group), feasible=len(feasible), feasible_rate=len(feasible)/len(group), errors=errors,
                optimal=sum(r["status"] == "optimal" and r["feasible"] for r in group),
                median_all=median(r["objective"] for r in feasible) if len(feasible) == len(group) else None,
                median_conditional=median(r["objective"] for r in feasible) if feasible else None,
                median_bp_gap_percent=(median(r["bp_gap_percent"] for r in feasible)
                    if feasible and all(r["bp_gap_percent"] is not None for r in feasible) else None),
                median_reference_gap_percent=(median(r["reference_gap_percent"] for r in feasible)
                    if feasible and all(r["reference_gap_percent"] is not None for r in feasible) else None),
                median_first_feasible_conditional=median(r["first_feasible_seconds"] for r in feasible)
                    if feasible else None, reference_optimum=reference)
            summaries.append(row)
            per_method[method] = row
        exact = per_method["exact"]
        for method, row in per_method.items():
            if method in ("exact", "compact"):
                continue
            comparable = (not row["errors"] and not exact["errors"]
                          and row["median_all"] is not None and exact["median_all"] is not None)
            comparisons.append(dict(batch=folder.name, instance=name, budget=manifest["limit"], method=method,
                completion_rows=formulation,
                feasible_rate=row["feasible_rate"], exact_feasible_rate=exact["feasible_rate"],
                errors=row["errors"] + exact["errors"],
                median_delta_vs_exact=row["median_all"]-exact["median_all"] if comparable else None))
    return runs, trajectories, summaries, comparisons


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results-dir", action="append", required=True)
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()
    tables = [[], [], [], []]
    for folder in args.results_dir:
        for combined, rows in zip(tables, collect(Path(folder))):
            combined.extend(rows)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=False)
    for name, rows in zip(("runs", "trajectories", "summary", "comparisons"), tables):
        write_csv(out / f"{name}.csv", rows)
    print(f"Reports: {out}; runs: {len(tables[0])}")


if __name__ == "__main__":
    main()
