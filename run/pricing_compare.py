"""Collect frozen pricing tasks, replay shared methods, and summarize every run.

Examples and the deliberately opt-in CIM command are in docs/pricing_comparison.md.
No credentials are imported from run.run, and collection always uses greedy.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _positive_int(value):
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return result


def _positive_float(value):
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise argparse.ArgumentTypeError("must be finite and positive")
    return result


def _clean(value):
    if isinstance(value, dict):
        return {str(key): _clean(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_clean(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(_clean(value), stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def _new_directory(path):
    directory = Path(path).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    return directory


@contextlib.contextmanager
def _environment(settings):
    previous = {key: os.environ.get(key) for key in settings}
    os.environ.update({key: str(value) for key, value in settings.items()})
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _discover_tasks(directory):
    from cg.pricing.pricing_snapshot import load_snapshot
    directory = Path(directory).resolve()
    if not directory.is_dir():
        raise FileNotFoundError(f"snapshot directory does not exist: {directory}")
    tasks = {}
    for path in sorted(directory.rglob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict) or not all(key in data for key in ("task_hash", "graph", "dual")):
            continue
        snapshot = load_snapshot(path)
        if not snapshot.get("completeness", {}).get("independently_replayable", False):
            raise ValueError(f"incomplete pricing snapshot: {path}; "
                             f"missing={snapshot.get('completeness', {}).get('missing')}")
        task_hash = snapshot["task_hash"]
        if task_hash not in tasks:
            tasks[task_hash] = dict(task_hash=task_hash, snapshot_path=str(path.resolve()),
                file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                phase=snapshot.get("phase"), context=snapshot.get("provenance", {}).get("context"))
    return list(tasks.values())


def collect(args):
    from bpc.branch_and_price import BranchAndPrice
    from cg import budget_clock
    from cg.pricing.pricing_snapshot import SnapshotLimitReached
    from ev.ev_to_pcp import ev_json_to_instance
    from experiments.run_instance import check_input
    instances = [Path(path).resolve() for path in args.instance]
    for path in instances:
        if not path.is_file():
            raise FileNotFoundError(f"instance does not exist: {path}")
    out = _new_directory(args.out_dir)
    outcomes = []
    started = time.perf_counter()
    # Disable primal callbacks that could terminate before the pricing snapshot,
    # and always override a caller's CIM provider for this offline collection.
    settings = dict(PRICING_SNAPSHOT_DIR=out, PRICING_SNAPSHOT_LIMIT=args.count,
        PRICING_SNAPSHOT_ROOT_ONLY="1", QAIA_PROVIDER="greedy",
        QAIA_EXACT_MODE="always", EXACT_POOL_SEARCH_MODE="0",
        BPC_PRIMAL_COMPLETION="0", BPC_NEIGHBORHOOD="0", BPC_RMP_MIP="0",
        BPC_CAPACITY_BOUND="0", BPC_DUMP_LP="0", BPC_VERBOSE="0")
    with _environment(settings), (out / "collection.log").open("x", encoding="utf-8") as log:
        for path in instances:
            before = len(_discover_tasks(out))
            if before >= args.count:
                break
            entry = dict(instance=str(path), seed=args.seed, limit_seconds=args.limit,
                         snapshots_before=before)
            try:
                raw = path.read_bytes()
                entry["instance_sha256"] = hashlib.sha256(raw).hexdigest()
                data = json.loads(raw)
                check_input(data)
                budget_clock.reset()
                deadline = budget_clock.now() + args.limit
                with _environment({"PRICING_SNAPSHOT_SOURCE_INSTANCE": str(path)}), \
                        contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                    instance = ev_json_to_instance(data, deadline=deadline)
                    bp = BranchAndPrice(instance.graph, instance.charger_num, args.limit,
                                        use_qaia=True, qaia_seed=args.seed)
                    result = bp.solve(deadline=deadline)
                entry.update(status=result["status"], error=result.get("error"))
            except SnapshotLimitReached as exc:
                entry.update(status="snapshot_limit_reached", error=None,
                             stopped_after_snapshot=str(getattr(exc, "last_path", "")))
            except Exception as exc:
                entry.update(status="error", error=repr(exc))
            entry["snapshots_after"] = len(_discover_tasks(out))
            outcomes.append(entry)
            print(json.dumps(entry, ensure_ascii=False), flush=True)
    tasks = _discover_tasks(out)
    manifest = dict(schema_version=1, created_utc=datetime.now(timezone.utc).isoformat(),
        requested_count=args.count, collected_count=len(tasks), root_only=True,
        provider="greedy", cloud_requests=0, task_limit_reached=len(tasks) >= args.count,
        wall_seconds=time.perf_counter()-started, instances=outcomes, tasks=tasks)
    _write_json(out / "collection.json", manifest)
    _write_json(out / "fixed_tasks.json", dict(schema_version=1, tasks=tasks[:args.count]))
    print(json.dumps(dict(snapshots=len(tasks), requested=args.count, directory=str(out),
        status="complete" if len(tasks) >= args.count else "insufficient_distinct_root_tasks",
        cloud_requests=0, fixed_tasks=str(out / "fixed_tasks.json")), ensure_ascii=False), flush=True)
    return 0 if len(tasks) >= args.count else 2


def _select_tasks(args):
    from cg.pricing.pricing_snapshot import load_snapshot
    if args.task_manifest:
        manifest = json.loads(Path(args.task_manifest).read_text(encoding="utf-8-sig"))
        tasks = manifest["tasks"]
        if args.task_limit < len(tasks):
            raise ValueError("--task-limit would truncate the frozen manifest; use its full task count")
        for task in tasks:
            path = Path(task["snapshot_path"])
            snapshot = load_snapshot(path)
            if not snapshot.get("completeness", {}).get("independently_replayable", False):
                raise ValueError(f"incomplete pricing snapshot in manifest: {path}")
            if snapshot["task_hash"] != task["task_hash"]:
                raise ValueError(f"task hash changed: {path}")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if task.get("file_sha256") != digest:
                raise ValueError(f"snapshot file changed after freezing: {path}")
    else:
        if not args.snapshots:
            raise ValueError("supply --snapshots or --task-manifest")
        tasks = _discover_tasks(args.snapshots)[:args.task_limit]
    if not tasks:
        raise ValueError("no complete pricing snapshots found")
    if len({task["task_hash"] for task in tasks}) != len(tasks):
        raise ValueError("frozen manifest contains duplicate task hashes")
    if args.require_tasks is not None and len(tasks) != args.require_tasks:
        raise ValueError(f"requires exactly {args.require_tasks} tasks; found {len(tasks)}")
    return tasks


def replay(args):
    from cg.pricing.pricing_replay import replay_task
    tasks = _select_tasks(args)
    if len(set(args.methods)) != len(args.methods):
        raise ValueError("duplicate methods are not independent repeats")
    use_new_cim = "cim" in args.methods and args.cim_mode == "new"
    if use_new_cim and not args.allow_new_cim:
        raise ValueError("new CIM requests require --allow-new-cim; default mode is cache")
    out = _new_directory(args.out_dir)
    expected = len(tasks) * args.repeats if use_new_cim else 0
    settings = dict(PRICING_SNAPSHOT_DIR="", CIM_MAX_CALLS="1")
    batch_id = out.name + "_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    manifest = dict(schema_version=1, batch_id=batch_id, tasks=tasks,
        methods=args.methods, repeats=args.repeats, base_seed=args.seed,
        expected_new_cim_requests_maximum=expected, automatic_retries=0,
        seed_rule="base_seed + repeat_index (same seed across methods and tasks)",
        arguments=vars(args))
    manifest["arguments"] = {key: value for key, value in manifest["arguments"].items()
                             if key != "handler"}
    _write_json(out / "fixed_tasks.json", dict(schema_version=1, tasks=tasks))
    _write_json(out / "batch.json", manifest)
    print(json.dumps(dict(tasks=len(tasks), repeats=args.repeats, methods=args.methods,
        maximum_new_cim_requests=expected, automatic_retries=0,
        cim_mode=args.cim_mode if "cim" in args.methods else None,
        output_directory=str(out)), ensure_ascii=False), flush=True)
    completed = []
    with _environment(settings), (out / "replay.log").open("x", encoding="utf-8") as log:
        for task_index, task in enumerate(tasks):
            for repeat in range(args.repeats):
                for method in args.methods:
                    path = out / f"task_{task_index:03d}_{task['task_hash'][:12]}_{method}_repeat_{repeat:03d}.json"
                    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                        record = replay_task(task["snapshot_path"], method,
                            seed=args.seed+repeat, sample_limit=args.sample_limit,
                            max_columns=args.max_columns, n_iter=args.n_iter,
                            time_limit=args.time_limit, cim_mode=args.cim_mode,
                            cache_dir=args.cache_dir)
                    record.update(batch_id=batch_id, task_index=task_index,
                                  repeat_index=repeat, planned_new_request=use_new_cim and method == "cim")
                    _write_json(path, record)
                    completed.append(path)
                    print(json.dumps(dict(task=task_index, repeat=repeat, method=method,
                        status=record.get("status"), error=record.get("error"), path=str(path)),
                        ensure_ascii=False), flush=True)
    _save_summary(completed, out)
    return 0


def _flatten(record):
    row = {key: record.get(key) for key in (
        "task_hash", "task_index", "repeat_index", "method", "seed", "status", "error",
        "request_status", "new_request_count", "backend_request_attempt_count",
        "actual_cloud_submission_count", "sample_source", "independent_repeat",
        "batch_identity", "batch_id", "snapshot_path")}
    if isinstance(row["batch_identity"], (dict, list)):
        row["batch_identity"] = json.dumps(row["batch_identity"], sort_keys=True, ensure_ascii=False)
    for section in ("metrics", "timing", "exact"):
        for key, value in (record.get(section) or {}).items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                row[f"{section}.{key}"] = value
    for name, ratio in (record.get("metrics", {}).get("ratios") or {}).items():
        for key in ("numerator", "denominator", "value"):
            row[f"ratio.{name}.{key}"] = ratio.get(key)
    for key, value in (record.get("config") or {}).items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            row[f"config.{key}"] = value
    for key, value in (record.get("replay_version") or {}).items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            row[f"replay_version.{key}"] = value
    return row


def _write_csv(path, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with Path(path).open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(_clean(rows))


def _aggregate(records):
    groups = defaultdict(list)
    for record in records:
        groups[(record.get("task_hash"), record.get("method"),
                record.get("sample_source", "unknown"))].append(record)
    rows = []
    for (task_hash, method, sample_source), runs in sorted(
            groups.items(), key=lambda item: tuple(str(value) for value in item[0])):
        statuses = Counter(str(run.get("status", "missing")) for run in runs)
        batch_values = [json.dumps(run.get("batch_identity"), sort_keys=True)
                        for run in runs if run.get("batch_identity") is not None]
        independent_batches = {json.dumps(run["batch_identity"], sort_keys=True)
            for run in runs if run.get("independent_repeat") and run.get("batch_identity") is not None}
        row = dict(task_hash=task_hash, method=method, sample_source=sample_source, run_count=len(runs),
            status_counts=json.dumps(dict(statuses), sort_keys=True),
            independent_repeat_count=len(independent_batches),
            independent_attempt_count=sum(bool(run.get("independent_repeat")) for run in runs),
            unique_raw_batch_count=len(set(batch_values)),
            request_status_counts=json.dumps(dict(Counter(
                str(run.get("request_status", "missing")) for run in runs)), sort_keys=True),
            replay_source_sha256s=json.dumps(sorted({run.get("replay_version", {}).get("source_sha256")
                for run in runs if run.get("replay_version", {}).get("source_sha256")}), sort_keys=True),
            denominator_for_per_run_means=len(runs))
        for counter in ("new_request_count", "backend_request_attempt_count", "actual_cloud_submission_count"):
            observed = [run.get(counter) for run in runs if isinstance(run.get(counter), (int, float))
                        and not isinstance(run.get(counter), bool) and math.isfinite(run.get(counter))]
            row[f"{counter}_known_sum"] = sum(observed)
            row[f"{counter}_observed_runs"] = len(observed)
            row[f"{counter}_unknown_runs"] = len(runs)-len(observed)
        metrics = sorted({key for run in runs for key, value in (run.get("metrics") or {}).items()
                          if isinstance(value, (int, float)) and not isinstance(value, bool)})
        for key in metrics:
            values = [run.get("metrics", {}).get(key) for run in runs]
            numbers = [value for value in values if isinstance(value, (int, float)) and math.isfinite(value)]
            row[f"metrics.{key}.observed_runs"] = len(numbers)
            if key.endswith("_reduced_cost"):
                # Empty/error runs have no meaningful RC; the denominator stays explicit.
                row[f"metrics.{key}.mean_observed"] = sum(numbers)/len(numbers) if numbers else None
                row[f"metrics.{key}.minimum_observed"] = min(numbers) if numbers else None
            else:
                row[f"metrics.{key}.sum"] = sum(numbers)
                row[f"metrics.{key}.mean_all_runs"] = sum(numbers)/len(runs)
        timings = sorted({key for run in runs for key in (run.get("timing") or {})})
        for key in timings:
            numbers = [run.get("timing", {}).get(key) for run in runs]
            numbers = [value for value in numbers if isinstance(value, (int, float)) and math.isfinite(value)]
            row[f"timing.{key}.observed_runs"] = len(numbers)
            row[f"timing.{key}.mean_all_runs"] = sum(numbers)/len(runs)
        ratios = sorted({name for run in runs for name in
                         (run.get("metrics", {}).get("ratios") or {})})
        for name in ratios:
            numerator = sum((run.get("metrics", {}).get("ratios", {}).get(name) or {}).get("numerator", 0)
                            for run in runs)
            denominator = sum((run.get("metrics", {}).get("ratios", {}).get(name) or {}).get("denominator", 0)
                              for run in runs)
            row[f"ratio.{name}.numerator_sum"] = numerator
            row[f"ratio.{name}.denominator_sum"] = denominator
            row[f"ratio.{name}.pooled_value"] = numerator/denominator if denominator else None
        rows.append(row)
    return rows


def _save_summary(paths, out):
    records = [json.loads(Path(path).read_text(encoding="utf-8-sig")) for path in paths]
    _write_csv(out / "runs.csv", [_flatten(record) for record in records])
    aggregates = _aggregate(records)
    _write_csv(out / "task_method_summary.csv", aggregates)
    summary = dict(schema_version=1, run_count=len(records),
        status_counts=dict(Counter(str(record.get("status", "missing")) for record in records)),
        failures_are_retained=True, cached_batches_are_not_independent_repeats=True,
        input_runs=[str(Path(path).resolve()) for path in paths], task_method_summary=aggregates)
    _write_json(out / "summary.json", summary)
    return summary


def summarize(args):
    paths = []
    seen = set()
    for source in args.runs:
        source = Path(source).resolve()
        candidates = [source] if source.is_file() else sorted(source.rglob("*.json"))
        for path in candidates:
            if path in seen:
                continue
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict) and all(key in data for key in ("task_hash", "method", "metrics")):
                paths.append(path)
                seen.add(path)
    if not paths:
        raise ValueError("no per-run pricing replay JSON files found")
    out = _new_directory(args.out_dir)
    summary = _save_summary(paths, out)
    print(json.dumps(dict(run_count=summary["run_count"], status_counts=summary["status_counts"],
                         runs_csv=str(out / "runs.csv"), output=str(out)), ensure_ascii=False), flush=True)
    return 0


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    p = commands.add_parser("collect", help="bounded root task capture; greedy only, no CIM calls")
    p.add_argument("--instance", action="append", required=True)
    p.add_argument("--out-dir", required=True, help="new directory; existing outputs are never overwritten")
    p.add_argument("--count", type=_positive_int, default=6)
    p.add_argument("--limit", type=_positive_float, default=60, help="seconds per instance, maximum")
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(handler=collect)
    p = commands.add_parser("replay", help="run every selected method on frozen tasks")
    selection = p.add_mutually_exclusive_group(required=True)
    selection.add_argument("--snapshots")
    selection.add_argument("--task-manifest", help="reuse exact fixed_tasks.json from collection or replay")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--methods", choices=["cim", "bsb", "sa", "random", "exact"], nargs="+",
                   default=["bsb", "sa", "random", "exact"])
    p.add_argument("--repeats", type=_positive_int, default=3)
    p.add_argument("--sample-limit", type=_positive_int, default=10)
    p.add_argument("--max-columns", type=_positive_int, default=3)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--n-iter", type=_positive_int, default=200)
    p.add_argument("--time-limit", type=_positive_float, default=60)
    p.add_argument("--task-limit", type=_positive_int, default=6)
    p.add_argument("--require-tasks", type=_positive_int)
    p.add_argument("--cim-mode", choices=["cache", "new"], default="cache")
    p.add_argument("--allow-new-cim", action="store_true")
    p.add_argument("--cache-dir", help="CIM cache input/output directory; never hidden as a repeat")
    p.set_defaults(handler=replay)
    p = commands.add_parser("summarize", help="retain successes, failures, empty and timeout runs")
    p.add_argument("--runs", action="append", required=True, help="repeat for multiple batches")
    p.add_argument("--out-dir", required=True)
    p.set_defaults(handler=summarize)
    return result


def main(argv=None):
    argument_parser = parser()
    args = argument_parser.parse_args(argv)
    try:
        return args.handler(args)
    except (ValueError, FileNotFoundError, FileExistsError) as exc:
        argument_parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
