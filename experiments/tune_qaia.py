"""Offline Optuna TPE tuning of fixed-budget BP solution quality.

Training solves have their own budgets. Neither their time nor Optuna overhead
is subtracted from or added to any later frozen-parameter BP run.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

from config.qaia_runtime import QAIA_ENV_KEYS

ROOT = Path(__file__).resolve().parents[1]


def quality_score(records, horizons):
    """Missing-count first, then bounded normalized quality of feasible runs.

    Missing objectives stay None in the raw data; they are not assigned a fake
    makespan. The scalar is a tuning loss, not a reported average objective.
    """
    valid = [bool(r.get("validation_passed") and r.get("has_feasible_solution")) for r in records]
    missing = len(records)-sum(valid)
    quality = sum(float(r["objective"])/h for r, h, ok in zip(records, horizons, valid) if ok)
    return missing + quality/(len(records)+1)


def main():
    import optuna
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", action="append", default=[])
    parser.add_argument("--instance-list")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--trials", type=int, default=30)
    parser.add_argument("--limit", type=float, default=120)
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--sampler-seed", type=int, default=2026)
    args = parser.parse_args()
    if args.instance_list:
        args.instance.extend(json.loads(Path(args.instance_list).read_text(encoding="utf-8-sig"))["instances"])
    if not args.instance or args.trials < 1 or not 0 < args.limit < float("inf"):
        parser.error("Supply training instances and positive trials/time")
    if min(args.seeds) < 0 or len(set(args.seeds)) != len(args.seeds):
        parser.error("seeds must be distinct nonnegative integers")
    # Fail before launching many trials if the real QAIA installation is missing.
    import qaia
    paths = [Path(p).resolve() for p in args.instance]
    out = Path(args.out_dir).resolve()
    out.mkdir(parents=True, exist_ok=False)
    inputs = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    training = [dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                     date=d.get("metadata", {}).get("local_arrival_date")) for p, d in zip(paths, inputs)]
    started = time.perf_counter()
    base = {k: v for k, v in os.environ.items() if k not in QAIA_ENV_KEYS}
    base.update(EXACT_POOL_SEARCH_MODE="0", BPC_COMPLETION_ROWS="vehicle",
                QAIA_PROVIDER="qaia", QAIA_EXACT_MODE="on_qaia_failure",
                QAIA_COLUMN_POLICY="combined", QAIA_MAX_COLUMNS="3", QAIA_MAX_STREAK="3")
    protocol_keys = ["EXACT_POOL_SEARCH_MODE", "BPC_COMPLETION_ROWS", "BPC_RMP_MIP",
                     "BPC_RMP_MIP_SECONDS", "BPC_RMP_MIP_FRACTION", "BPC_RMP_MIP_EVERY",
                     "BPC_PRIMAL_COMPLETION", "BPC_PRIMAL_SECONDS", "BPC_PRIMAL_ATTEMPTS"]
    protocol = {k: base.get(k) for k in protocol_keys}
    study = optuna.create_study(direction="minimize",
        sampler=optuna.samplers.TPESampler(seed=args.sampler_seed),
        storage="sqlite:///"+(out/"study.sqlite3").as_posix(), study_name="bp_qaia")
    study.enqueue_trial(dict(n_iter=200, batch_size=10, dt=1.0, xi_mode="auto"))

    def objective(trial):
        env = dict(base)
        env.update(QAIA_N_ITER=str(trial.suggest_categorical("n_iter", [50, 200, 500, 1000, 2000])),
            QAIA_BATCH_SIZE=str(trial.suggest_categorical("batch_size", [4, 10, 20, 50])),
            QAIA_DT=str(trial.suggest_float("dt", 0.05, 1.5)),
            QAIA_XI="auto")
        if trial.suggest_categorical("xi_mode", ["auto", "tuned"]) == "tuned":
            env["QAIA_XI"] = str(trial.suggest_float("xi", 0.1, 2.0))
        trial.set_user_attr("env", {k: env[k] for k in QAIA_ENV_KEYS})
        records, horizons = [], []
        directory = out/f"trial_{trial.number:03d}"
        directory.mkdir()
        for i, (path, data) in enumerate(zip(paths, inputs)):
            for seed in args.seeds:
                target = directory/f"instance_{i:03d}_s{seed}.json"
                subprocess.run([sys.executable, "-m", "experiments.run_instance",
                    "--instance", str(path), "--method", "qaia_root", "--seed", str(seed),
                    "--limit", str(args.limit), "--out", str(target)],
                    cwd=ROOT, env=env, check=True, timeout=args.limit+60)
                record = json.loads(target.read_text(encoding="utf-8"))
                if record["status"] == "error":
                    raise RuntimeError(f"Training run failed: {target}; {record.get('error')}")
                records.append(record)
                horizons.append(data["time_horizon"])
        trial.set_user_attr("feasible_count", sum(r["has_feasible_solution"] for r in records))
        trial.set_user_attr("objectives", [r.get("objective") for r in records])
        trial.set_user_attr("mean_bp_seconds", statistics.mean(r["wall_seconds"] for r in records))
        return quality_score(records, horizons)

    completed = False
    try:
        study.optimize(objective, n_trials=args.trials)
        completed = True
    finally:
        elapsed = time.perf_counter()-started
        trials = [dict(number=t.number, value=t.value, params=t.params,
                       state=t.state.name,
                       seconds=t.duration.total_seconds() if t.duration else None,
                       **t.user_attrs) for t in study.trials]
        (out/"trials.json").write_text(json.dumps(trials, indent=2), encoding="utf-8")
        (out/"tuning_run.json").write_text(json.dumps(dict(completed=completed,
            tuning_seconds=elapsed, training_instances=training, protocol=protocol), indent=2), encoding="utf-8")
    if study.best_trial.user_attrs["feasible_count"] == 0:
        raise RuntimeError("No training run found a feasible solution; inspect trials before freezing parameters")
    frozen = dict(schema_version="qaia-frozen-v1", env=study.best_trial.user_attrs["env"],
        tuning_seconds=elapsed, training_instances=training, training_limit=args.limit,
        training_seeds=args.seeds, sampler_seed=args.sampler_seed, protocol=protocol,
        best_trial=study.best_trial.number, best_tuning_loss=study.best_value,
        loss_definition="missing_count + sum(feasible_objective/horizon)/(run_count+1)")
    (out/"best_qaia.json").write_text(json.dumps(frozen, indent=2), encoding="utf-8")
    print(f"Frozen configuration: {out/'best_qaia.json'}; offline tuning: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
