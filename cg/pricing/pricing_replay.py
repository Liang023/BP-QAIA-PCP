"""Replay a frozen pricing task and separate sampling from shared repair.

SA uses NumPy only: independent chains, random-permutation single-spin Metropolis
sweeps and a geometric temperature schedule. One sweep proposes n flips/chain.
Neither QUBO energy nor a repaired weight is used to certify an original column.
"""
from __future__ import annotations

import hashlib
import json
import math
from importlib import metadata
from pathlib import Path
import platform
import time

import numpy as np
from scipy.sparse import csr_matrix

from cg import budget_clock
from cg.pricing.qaia_exact_pricing_solver import QAIAPricingSolver
from cg.pricing.pricing_snapshot import load_snapshot, restore_snapshot


_REPLAY_VERSION = None


def replay_version():
    global _REPLAY_VERSION
    if _REPLAY_VERSION is None:
        root = Path(__file__).resolve().parents[2]
        digest = hashlib.sha256()
        for name in ("cg/pricing/pricing_replay.py", "cg/pricing/pricing_snapshot.py",
                     "cg/pricing/qaia_exact_pricing_solver.py", "cg/pricing/exact_pricing_solver.py",
                     "cg/pricing/cim_worker.py", "cg/pricing/cim_backend.py", "qaia/QAIA.py", "qaia/SB.py"):
            digest.update(name.encode() + b"\0" + (root / name).read_bytes() + b"\0")
        packages = {}
        for name in ("numpy", "scipy", "gurobipy", "mindquantum", "kaiwu"):
            try:
                packages[name] = metadata.version(name)
            except metadata.PackageNotFoundError:
                packages[name] = None
        _REPLAY_VERSION = dict(source_sha256=digest.hexdigest(), python=platform.python_version(),
                               packages=packages, schema="pricing-replay-v1")
    return _REPLAY_VERSION


def _finite(value):
    return float(value) if value is not None and math.isfinite(float(value)) else None


def original_reduced_cost(problem, selected):
    """Real columns cost zero in every saved phase; expand merged originals."""
    dual = problem.dual
    score = float(dual.get("charger", 0.0))
    for identifier in selected:
        representative = problem.auxiliary_graph.vertices_map[identifier]
        for vertex in problem.auxiliary_graph.get_original_vertices(representative):
            score += float(dual.get("partition", {}).get(vertex.associated_partition.id, 0.0))
            score -= float(dual.get("makespan", {}).get(vertex.id, 0.0)) * vertex.end_time
    return -score


def inspect_set(problem, selected, adjacency, forbidden):
    selected = set(selected)
    conflicts = sum(v in forbidden for v in selected)
    conflicts += sum(u < v and v in selected for u in selected for v in adjacency[u])
    originals = [v for identifier in selected for v in
                 problem.auxiliary_graph.get_original_vertices(
                     problem.auxiliary_graph.vertices_map[identifier])]
    partition_ids = [v.associated_partition.id for v in originals]
    partition_violations = len(partition_ids) - len(set(partition_ids))
    legal = conflicts == 0 and partition_violations == 0
    return dict(selected=sorted(selected), legal=legal, conflict_count=int(conflicts),
                partition_violation_count=partition_violations,
                reduced_cost=original_reduced_cost(problem, selected) if legal else None)


def evaluate_samples(problem, solver, samples, *, excluded=(), epsilon=1e-6,
                     max_columns=3, prebuilt_model=None):
    """Evaluate binary sample columns, using the existing production repair."""
    ids, weights, adjacency, forbidden, _, _ = (prebuilt_model if prebuilt_model is not None
                                               else solver._build_ising_model())
    samples = np.asarray(samples)
    if samples.ndim != 2 or samples.shape[0] != len(ids):
        raise ValueError(f"Expected ({len(ids)}, samples), received {samples.shape}")
    excluded = {tuple(sorted(s)) for s in excluded}
    raw_unique, repaired_unique, raw_legal, negative, new = set(), {}, 0, {}, {}
    raw_negative, raw_new = {}, {}
    rows = []
    nonfinite = 0
    repair_seconds = 0.0
    for index, sample in enumerate(samples.T):
        if not np.isfinite(sample).all() or not np.isin(sample, [0, 1]).all():
            nonfinite += 1
            rows.append(dict(sample_index=index, status="invalid_output",
                             raw=dict(selected=None, legal=False, conflict_count=None,
                                      reduced_cost=None), repaired=None))
            continue
        initial = {ids[i] for i, value in enumerate(sample) if value == 1}
        raw = inspect_set(problem, initial, adjacency, forbidden)
        raw_unique.add(tuple(sorted(initial)))
        raw_legal += int(raw["legal"])
        if initial and raw["legal"] and raw["reduced_cost"] < -epsilon:
            raw_signature = tuple(sorted(initial))
            raw_negative[raw_signature] = raw["reduced_cost"]
            if raw_signature not in excluded:
                raw_new[raw_signature] = raw["reduced_cost"]
        repair_started = time.perf_counter()
        repaired_set = solver._repair_independent_set(initial, ids, weights, adjacency, forbidden)
        repair_seconds += time.perf_counter() - repair_started
        repaired = inspect_set(problem, repaired_set, adjacency, forbidden)
        repaired.update(removed=sorted(initial - repaired_set), added=sorted(repaired_set - initial),
                        modification_count=len(initial.symmetric_difference(repaired_set)))
        signature = tuple(sorted(repaired_set))
        if repaired["legal"]:
            repaired_unique[signature] = repaired["reduced_cost"]
            if signature and repaired["reduced_cost"] < -epsilon:
                negative[signature] = repaired["reduced_cost"]
                if signature not in excluded:
                    new[signature] = repaired["reduced_cost"]
        rows.append(dict(sample_index=index, status="evaluated", raw=raw, repaired=repaired,
                         already_in_pool=signature in excluded))
    ranked = sorted(new.items(), key=lambda item: (item[1], item[0]))[:max_columns]
    count = samples.shape[1]
    def ratio(numerator, denominator):
        return dict(numerator=numerator, denominator=denominator,
                    value=numerator / denominator if denominator else None)
    # Best legal RC is over both pre-repair and post-repair observations.
    legal_rc = [row["raw"]["reduced_cost"] for row in rows if row["raw"]["legal"]]
    legal_rc += list(repaired_unique.values())
    metrics = dict(raw_sample_count=count, raw_unique_count=len(raw_unique),
                   raw_legal_sample_count=raw_legal, invalid_sample_count=nonfinite,
                   raw_unique_negative_reduced_cost_count=len(raw_negative),
                   raw_effective_new_column_count=len(raw_new),
                   repaired_unique_legal_count=len(repaired_unique),
                   unique_negative_reduced_cost_count=len(negative),
                   effective_new_column_count=len(new), returned_column_count=len(ranked),
                   best_legal_reduced_cost=min(legal_rc) if legal_rc else None,
                   best_raw_legal_reduced_cost=min(
                       [r["raw"]["reduced_cost"] for r in rows if r["raw"]["legal"]], default=None),
                   best_repaired_legal_reduced_cost=min(repaired_unique.values(), default=None),
                   ratios=dict(raw_legality=ratio(raw_legal, count),
                               raw_uniqueness=ratio(len(raw_unique), count),
                               raw_new_column_yield=ratio(len(raw_new), count),
                               repaired_unique_yield=ratio(len(repaired_unique), count),
                               negative_among_unique_repaired=ratio(len(negative), len(repaired_unique)),
                               new_among_unique_negative=ratio(len(new), len(negative)),
                               new_column_yield=ratio(len(new), count)))
    return dict(metrics=metrics, per_sample=rows,
                evaluation_timing=dict(repair_seconds=repair_seconds),
                returned_columns=[dict(selected=list(s), reduced_cost=rc) for s, rc in ranked])


def simulated_annealing(j_mat, h_vec, *, sample_limit, n_iter, seed, deadline,
                        temperature_start=2.0, temperature_end=0.01):
    """Geometric schedule on normalized H=-.5*s'Js-h's; n_iter sweeps."""
    if not 0 < temperature_end <= temperature_start:
        raise ValueError("SA requires 0 < end temperature <= start temperature")
    rng = np.random.default_rng(seed)
    j = np.asarray(j_mat.toarray(), dtype=float)
    h = np.asarray(h_vec, dtype=float)
    spins = 2 * rng.integers(0, 2, size=(len(h), sample_limit), dtype=np.int8) - 1
    field = j @ spins + h[:, None]
    sweeps = 0
    for temperature in np.geomspace(temperature_start, temperature_end, n_iter):
        if time.perf_counter() >= deadline:
            break
        for i in rng.permutation(len(h)):
            delta = 2.0 * spins[i] * field[i]
            accept = (delta <= 0) | (rng.random(sample_limit) < np.exp(-np.maximum(delta, 0) / temperature))
            change = np.where(accept, -2 * spins[i], 0)
            spins[i] += change
            field += j[:, i, None] * change[None, :]
        sweeps += 1
    return ((spins + 1) // 2).astype(np.int8), dict(
        dependency="numpy", temperature_schedule="geometric", temperature_start=temperature_start,
        temperature_end=temperature_end, requested_sweeps=n_iter, completed_sweeps=sweeps,
        proposed_flip_budget=n_iter * len(h) * sample_limit,
        completed_proposals=sweeps * len(h) * sample_limit, seed=seed,
        timed_out=sweeps < n_iter)


def _request_matches(request, ids, weights, adjacency, forbidden, penalty):
    return (request.get("ids") == ids
            and request.get("weights") == [weights[v] for v in ids]
            and sorted(map(tuple, request.get("edges", []))) ==
                sorted((u, v) for u in ids for v in adjacency[u] if u < v)
            and request.get("forbidden") == sorted(forbidden)
            and request.get("penalty") == penalty)


def _cached_samples(directory, ids, weights, adjacency, forbidden, penalty):
    paths = sorted(Path(directory).rglob("request.json"))
    malformed_requests = []
    for path in paths:
        try:
            request = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            malformed_requests.append(dict(path=str(path), error=str(exc)))
            continue
        if not _request_matches(request, ids, weights, adjacency, forbidden, penalty):
            continue
        sample_path = path.parent / "samples.npy"
        if not sample_path.exists():
            continue
        samples = np.load(sample_path, allow_pickle=False)
        metadata = dict(directory=str(path.parent.resolve()), request=request,
                        original_task=request.get("task"),
                        complete_historical_snapshot=False,
                        binding="exact sampler encoding match; objective/pool supplied by current snapshot")
        metadata["malformed_requests_encountered"] = malformed_requests
        for name in ("cloud_timing", "status", "sdk_metadata", "encoding_metadata"):
            source = path.parent / f"{name}.json"
            if source.exists():
                try:
                    metadata[name] = json.loads(source.read_text(encoding="utf-8"))
                except (ValueError, OSError) as exc:
                    metadata[name] = dict(status="invalid_metadata", error=str(exc))
        return samples, metadata, hashlib.sha256(sample_path.read_bytes()).hexdigest()
    raise FileNotFoundError(f"No cached binary samples match this snapshot's complete sampler encoding; malformed requests={len(malformed_requests)}")


def _exact_samples(graph, problem, *, max_columns, time_limit, seed):
    import gurobipy as grb
    from cg.pricing.exact_pricing_solver import ExactPricingSolver
    solver = ExactPricingSolver(graph, problem)
    model = solver.model
    try:
        solver.pool_sol_num = max_columns
        solver.set_objective()
        model.Params.Seed = seed
        timed_out = False
        try:
            solver.solve(budget_clock.now() + max(0.001, time_limit))
        except TimeoutError:
            timed_out = True
        code = model.Status
        names = {grb.GRB.OPTIMAL: "optimal", grb.GRB.TIME_LIMIT: "time_limit",
                 grb.GRB.INFEASIBLE: "infeasible", grb.GRB.INTERRUPTED: "interrupted"}
        ids = sorted(graph.vertices_map)
        samples = np.empty((len(ids), model.SolCount), dtype=np.int8)
        for i in range(model.SolCount):
            model.Params.SolutionNumber = i
            samples[:, i] = [int(solver.vars[v].Xn > 0.5) for v in ids]
        incumbent = _finite(model.ObjVal) if model.SolCount else None
        bound = _finite(model.ObjBound)
        constant = -float(problem.dual.get("charger", 0.0))
        exact = dict(status=names.get(code, f"gurobi_{code}"), status_code=code,
                     maximum_weight=incumbent, weight_upper_bound=bound,
                     incumbent_reduced_cost=constant-incumbent if incumbent is not None else None,
                     optimal_reduced_cost=constant-incumbent if code == grb.GRB.OPTIMAL and incumbent is not None else None,
                     reduced_cost_lower_bound=constant-bound if bound is not None else None,
                     optimality_proven=code == grb.GRB.OPTIMAL,
                     time_limit_seconds=time_limit, pool_solution_limit=max_columns,
                     objective="original constraint MWIS; no QUBO penalty",
                     timed_out=timed_out)
        return samples, exact
    finally:
        model.dispose()


def replay_task(snapshot_path, method, *, seed=0, sample_limit=10, max_columns=3,
                n_iter=200, time_limit=60, cim_mode="cache", cache_dir=None,
                sa_temperature_start=2.0, sa_temperature_end=0.01):
    """Always return an auditable result, including failure/timeout/empty runs."""
    started = time.perf_counter()
    result = dict(snapshot_path=str(Path(snapshot_path).resolve()), task_hash=None,
                  method=method, seed=seed, status="error", error=None,
                  request_status="not_applicable", new_request_count=0,
                  backend_request_attempt_count=0, actual_cloud_submission_count=0,
                  independent_repeat=method != "cim" or cim_mode == "new",
                  sample_source="new_cloud" if method == "cim" and cim_mode == "new" else
                                "cached_cloud" if method == "cim" else "local",
                  batch_identity=None, config=dict(sample_limit=sample_limit, max_columns=max_columns,
                      n_iter=n_iter, time_limit=time_limit, seed=seed, cim_mode=cim_mode,
                      retries=0, sample_cap_policy="first returned samples, before shared repair"),
                  encoding={}, exact=None, metrics=dict(received_sample_count=0, raw_sample_count=0,
                      raw_unique_count=0, raw_legal_sample_count=0, repaired_unique_legal_count=0,
                      unique_negative_reduced_cost_count=0, effective_new_column_count=0,
                      returned_column_count=0, best_legal_reduced_cost=None),
                  timing=dict(encoding_seconds=0.0, sampling_seconds=0.0, repair_seconds=0.0,
                              wall_seconds=0.0), per_sample=[], returned_columns=[], raw_output=None,
                  replay_version=replay_version())
    stage_started, stage_name = started, "encoding_seconds"
    cim_backend = None
    directory = None
    try:
        if sample_limit <= 0 or max_columns <= 0 or n_iter <= 0 or time_limit <= 0:
            raise ValueError("Replay budgets must be positive")
        payload = load_snapshot(snapshot_path)
        result["task_hash"] = payload["task_hash"]
        if not payload.get("completeness", {}).get("independently_replayable"):
            raise ValueError(f"Incomplete pricing snapshot: {payload.get('completeness')}")
        result["phase"] = payload["phase"]
        graph, problem = restore_snapshot(payload)
        config = payload["config"]
        solver = QAIAPricingSolver(graph, problem, provider="greedy", algorithm="BSB",
                    batch_size=sample_limit, max_columns=max_columns, n_iter=n_iter,
                    random_seed=seed, backend=config.get("backend", "cpu-float32"),
                    penalty_margin=config.get("penalty_margin", 1.0),
                    normalize_ising=config.get("normalize_ising", True),
                    algorithm_kwargs=config.get("algorithm_kwargs", {"dt": 1.0}))
        ids, weights, adjacency, forbidden, j_mat, h_vec = solver._build_ising_model()
        encoding = payload["encoding"]
        saved_j, saved_h = np.asarray(encoding["J"]), np.asarray(encoding["h"])
        if not np.allclose(j_mat.toarray(), saved_j, rtol=0, atol=1e-12) or not np.allclose(h_vec, saved_h, rtol=0, atol=1e-12):
            raise ValueError("Rebuilt classical encoding differs from snapshot")
        result["encoding"] = dict(snapshot_encoding=encoding, classical_input=dict(
            J=saved_j.tolist(), h=saved_h.tolist(), dtype="float64",
            backend=solver.backend, backend_internal_dtype="recorded from instantiated solver for BSB"),
            cim_input=None, quantization=dict(applied=False, scope="classical input is unquantized"))
        result["config"]["epsilon"] = float(config.get("epsilon", 1e-6))
        result["config"]["algorithm_kwargs"] = solver.algorithm_kwargs
        result["timing"][stage_name] = time.perf_counter() - stage_started
        stage_name, stage_started = "sampling_seconds", time.perf_counter()
        deadline = started + time_limit
        if method == "random":
            samples = solver._random_samples(len(ids), sample_limit, seed)
            raw = samples
            result["config"]["random_protocol"] = "existing provider=greedy; uniform binary starts; first sample all-zero"
        elif method == "bsb":
            solver.calls = 1
            solver.record_replay_input = True
            raw = solver._run_qaia(csr_matrix(saved_j), saved_h)
            if hasattr(raw, "detach"):
                raw = raw.detach().cpu().numpy()
            raw = np.asarray(raw)
            result["encoding"]["bsb_actual_input"] = getattr(solver, "last_qaia_input", None)
            result["encoding"]["bsb_state_dtype"] = str(raw.dtype)
            if raw.ndim == 1:
                raw = raw[:, None]
            samples = np.where(raw >= 0, 1, 0).astype(float)
            samples[:, ~np.isfinite(raw).all(axis=0)] = np.nan
        elif method == "sa":
            samples, sa = simulated_annealing(csr_matrix(saved_j), saved_h,
                sample_limit=sample_limit, n_iter=n_iter, seed=seed, deadline=deadline,
                temperature_start=sa_temperature_start, temperature_end=sa_temperature_end)
            raw = samples
            result["config"]["sa"] = sa
        elif method == "exact":
            samples, result["exact"] = _exact_samples(graph, problem, max_columns=max_columns,
                time_limit=max(0.001, deadline-time.perf_counter()), seed=seed)
            raw = samples
        elif method == "cim":
            result["config"]["seed_scope"] = "repeat seed recorded; hardware seed is not exposed by eCloud adapter"
            if cim_mode == "cache":
                from cg.pricing.cim_backend import cim_options
                samples, metadata, identity = _cached_samples(cache_dir or cim_options()["cache_dir"],
                    ids, weights, adjacency, forbidden, encoding["penalty"])
                result["cim"] = metadata
                result["batch_identity"] = identity
                order = metadata.get("encoding_metadata", {}).get("decoded_sample_order")
                if samples.shape[1] > sample_limit:
                    if order is None or len(order) != samples.shape[1]:
                        raise ValueError("Legacy cache was energy-sorted before sample cap; physical order unavailable. Increase common sample-limit to cover full batch.")
                    samples = samples[:, np.argsort(order)]
                    result["config"]["sample_cap_policy"] = "restored physical cached order, capped before energy selection"
            elif cim_mode == "new":
                from cg.pricing.cim_backend import CIMBackend
                cim_backend = CIMBackend()
                cim_backend.options["max_calls"] = 1
                if cache_dir:
                    cim_backend.options["cache_dir"] = str(cache_dir)
                samples = cim_backend.sample(ids, weights, adjacency, forbidden, solver.penalty_margin,
                    budget_clock.now()+time_limit, wall_timeout=max(0.001, deadline-time.perf_counter()),
                    request_context=dict(snapshot_task_hash=payload["task_hash"], seed=seed,
                                         sample_limit=sample_limit, strict_no_retry=True))
                result["cim"] = cim_backend.metrics
                if cim_backend.metrics["tasks"]:
                    directory = Path(cim_backend.metrics["tasks"][-1]["directory"])
                    result["batch_identity"] = cim_backend.metrics["tasks"][-1]["task"]
                    result["encoding"]["cim_input"] = str(directory)
                else:
                    result["cim"]["skip_reason"] = "device_size" if cim_backend.metrics["size_skips"] else "request_cap"
            else:
                raise ValueError("cim_mode must be cache or new")
            raw = samples
            directory = Path(result["cim"]["directory"]) if cim_mode == "cache" else directory
            meta_path = directory / "encoding_metadata.json" if directory is not None else None
            if meta_path is not None and meta_path.is_file():
                result["encoding"]["quantization"] = json.loads(meta_path.read_text(encoding="utf-8"))
                result["encoding"]["cim_input"] = str(directory.resolve())
            else:
                result["encoding"]["quantization"] = dict(applied=True, actual_device_input_saved=False,
                    status="legacy cache lacks quantized matrix; difference cannot be recovered")
        else:
            raise ValueError(f"Unknown replay method {method}")
        samples = np.asarray(samples)
        result["raw_output"] = dict(shape=list(np.asarray(raw).shape), values=
            [[_finite(v) for v in row] for row in np.atleast_2d(raw)],
            representation="continuous_state" if method == "bsb" else "binary")
        if samples.ndim != 2 or samples.shape[0] != len(ids):
            raise ValueError(f"Unexpected sample matrix shape {samples.shape}")
        received_count = samples.shape[1]
        if method == "cim" and directory is not None:
            sdk_meta = directory / "sdk_metadata.json"
            if sdk_meta.is_file():
                sdk_meta = json.loads(sdk_meta.read_text(encoding="utf-8"))
                received_count = int(sdk_meta.get("received_samples", received_count))
        result["timing"][stage_name] = time.perf_counter() - stage_started
        if method == "cim" and cim_mode == "new":
            device_encoding = result["encoding"]["quantization"]
            result["timing"]["device_encoding_seconds"] = device_encoding.get("encoding_seconds")
            result["timing"]["device_call_seconds"] = device_encoding.get("device_call_seconds")
        stage_name, stage_started = "repair_seconds", time.perf_counter()
        # All sampled methods use the same maximum number of starts and columns.
        # Exact's optimal incumbent/bound are separately retained before this cap.
        evaluation = evaluate_samples(problem, solver, samples[:, :sample_limit],
            excluded=payload["pool_signatures"], epsilon=result["config"]["epsilon"],
            max_columns=max_columns, prebuilt_model=(ids, weights, adjacency, forbidden, j_mat, h_vec))
        repair_elapsed = evaluation.pop("evaluation_timing")["repair_seconds"]
        result.update(evaluation)
        result["metrics"]["received_sample_count"] = received_count
        result["timing"][stage_name] = repair_elapsed
        result["timing"]["evaluation_seconds"] = max(0.0, time.perf_counter() - stage_started - repair_elapsed)
        stage_name = None
        result["status"] = "empty" if received_count == 0 else "completed"
        if method == "exact":
            result["status"] = result["exact"]["status"]
        if method == "sa" and result["config"]["sa"]["timed_out"]:
            result["status"] = "time_limit"
        elif time.perf_counter() > deadline:
            result["status"] = "time_limit"
        if result["batch_identity"] is None:
            result["batch_identity"] = hashlib.sha256(
                (payload["task_hash"] + method + str(seed)).encode() + np.asarray(samples).tobytes()).hexdigest()
    except TimeoutError as exc:
        result.update(status="time_limit", error=str(exc))
    except Exception as exc:
        result.update(status="error", error=f"{type(exc).__name__}: {exc}")
    finally:
        if stage_name:
            result["timing"][stage_name] = time.perf_counter() - stage_started
        if cim_backend is not None:
            result["cim"] = cim_backend.metrics
            result["new_request_count"] = cim_backend.metrics["requests"]
            result["backend_request_attempt_count"] = cim_backend.metrics["requests"]
            result["actual_cloud_submission_count"] = None if cim_backend.metrics["requests"] else 0
            tasks = cim_backend.metrics["tasks"]
            result["request_status"] = tasks[-1]["status"] if tasks else "not_submitted"
            if tasks:
                directory = Path(tasks[-1]["directory"])
                result["cim_artifact_directory"] = str(directory)
                result["cim_raw_artifact_paths"] = {name: str(directory / name) for name in
                    ("device_output_spins.npy", "raw_spins.npy", "samples.npy", "sdk_ising_matrix.npy", "pre_quantization_matrix.npy", "device_input_matrix.npy")
                    if (directory / name).is_file()}
                result["batch_identity"] = tasks[-1]["task"]
                for name in ("encoding_metadata", "cloud_timing", "sdk_metadata"):
                    source = directory / f"{name}.json"
                    if source.is_file():
                        try:
                            result.setdefault("cim_artifacts", {})[name] = json.loads(source.read_text(encoding="utf-8"))
                        except (ValueError, OSError) as exc:
                            result.setdefault("cim_artifacts", {})[name] = dict(error=str(exc))
                if "encoding_metadata" in result.get("cim_artifacts", {}):
                    result["encoding"]["quantization"] = result["cim_artifacts"]["encoding_metadata"]
                    metadata = result["cim_artifacts"]["encoding_metadata"]
                    result["actual_cloud_submission_count"] = metadata.get("submission_attempts")
                    result["timing"]["device_encoding_seconds"] = metadata.get("encoding_seconds")
                    result["timing"]["device_call_seconds"] = metadata.get("device_call_seconds")
                else:
                    result["encoding"]["quantization"] = dict(applied=None,
                        actual_device_input_saved=False, status="worker failed before encoding metadata was recorded")
        elif method == "cim":
            result["request_status"] = "cache_loaded" if "cim" in result else "cache_missing_or_error"
        result["timing"]["wall_seconds"] = time.perf_counter() - started
    return result
