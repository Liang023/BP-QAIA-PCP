"""Serializable pricing tasks captured before any heuristic sampling.

The task identity includes the phase, effective/raw duals, active graph and
original-vertex mapping, existing real-column pool and encoding.  Capturing the
same task again is a duplicate, even if its run seed or CG iteration differs.
Different phases always have different identities.  No Gurobi object is saved.
"""
from __future__ import annotations

from datetime import datetime, timezone
from importlib import metadata
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time
from typing import Any

import numpy as np

from cg.pricing.pricing_problem import PricingProblem
from model.a_graph import AuxiliaryGraph
from model.edge import Edge
from model.graph import Graph
from model.partition import Partition
from model.vertex import Vertex


SCHEMA = "bp-qaia-pricing-snapshot-v1"
IDENTITY_FIELDS = ("graph", "phase", "dual", "raw_master_duals", "weights", "reduced_cost",
                   "branch_constraints", "pool_signatures", "pool_original_signatures",
                   "encoding")
_VERSION = None


class SnapshotLimitReached(BaseException):
    """Normal collector exit, deliberately outside the BP failure catch path."""

    def __init__(self, directory, count, last_path=None):
        self.directory = str(directory)
        self.count = count
        self.last_path = str(last_path) if last_path is not None else None
        super().__init__(f"Collected {count} unique pricing snapshots in {directory}")


def _json_value(value: Any):
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, set):
        return [_json_value(item) for item in sorted(value)]
    if isinstance(value, np.ndarray):
        return _json_value(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    return value


def _canonical(value):
    return json.dumps(_json_value(value), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def task_hash(payload):
    """Hash task semantics; source path, time, seed and solver are provenance."""
    identity = {key: payload[key] for key in IDENTITY_FIELDS}
    # These affect the binary encoding; iteration/sample budgets do not.
    identity["encoding_config"] = {
        key: payload["config"][key]
        for key in ("penalty_margin", "normalize_ising", "epsilon")
    }
    return hashlib.sha256(_canonical(identity).encode("utf-8")).hexdigest()


def _versions():
    global _VERSION
    if _VERSION is None:
        root = Path(__file__).resolve().parents[2]
        git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                             capture_output=True, text=True, check=False)
        status = subprocess.run(["git", "status", "--porcelain"], cwd=root,
                                capture_output=True, text=True, check=False)
        source_digest = hashlib.sha256()
        for relative in ("cg/pricing/pricing_snapshot.py", "cg/pricing/qaia_exact_pricing_solver.py",
                         "cg/pricing/exact_pricing_solver.py", "cg/pricing/pricing_problem.py",
                         "cg/master/master_problem.py", "cg/column_generation.py", "model/a_graph.py"):
            source_digest.update(relative.encode("utf-8"))
            source_digest.update((root / relative).read_bytes())
        packages = {}
        for package in ("numpy", "scipy", "gurobipy", "qaia", "mindquantum"):
            try:
                packages[package] = metadata.version(package)
            except metadata.PackageNotFoundError:
                packages[package] = None
        _VERSION = {"git_commit": git.stdout.strip() if git.returncode == 0 else None,
                    "git_worktree_dirty": bool(status.stdout.strip()) if status.returncode == 0 else None,
                    "pricing_source_sha256": source_digest.hexdigest(),
                    "python": platform.python_version(), "packages": packages,
                    "snapshot_schema": SCHEMA}
    return dict(_VERSION)


def _edges(edges):
    return [list(edge) for edge in sorted({tuple(sorted((e.source.id, e.target.id)))
                                        for e in edges})]


def _vertex_record(vertex):
    partition = getattr(vertex, "associated_partition", None)
    return {"id": int(vertex.id), "end_time": float(vertex.end_time),
            "partition_id": None if partition is None else int(partition.id)}


def _graph_record(auxiliary):
    original = sorted(auxiliary.graph.vertices, key=lambda vertex: vertex.id)
    active = sorted(auxiliary.vertices_map.values(), key=lambda vertex: vertex.id)
    return {
        "original_vertices": [_vertex_record(vertex) for vertex in original],
        "partitions": [{"id": int(partition.id),
                        "vertex_ids": sorted(vertex.id for vertex in partition.vertex_list)}
                       for partition in sorted(auxiliary.graph.partitions,
                                               key=lambda partition: partition.id)],
        "original_edges": _edges(auxiliary.graph.edges),
        "active_vertices": [_vertex_record(vertex) for vertex in active],
        "auxiliary_edges": _edges(auxiliary.auxiliary_edges),
        "original_vertex_mapping": {
            str(vertex.id): sorted(original.id for original
                                   in auxiliary.get_original_vertices(vertex))
            for vertex in active},
    }


def _branch_record(auxiliary, graph):
    active_originals = {original for originals in graph["original_vertex_mapping"].values()
                        for original in originals}
    root_auxiliary = AuxiliaryGraph(auxiliary.graph, auxiliary.graph.vertex_map)
    base_edges = {tuple(edge) for edge in _edges(root_auxiliary.auxiliary_edges)}
    effective_edges = {tuple(edge) for edge in graph["auxiliary_edges"]}
    return {
        "representation": "effective_graph_constraints",
        "removed_original_vertices": sorted(set(auxiliary.graph.vertex_map) - active_originals),
        "merged_groups": {key: value for key, value in graph["original_vertex_mapping"].items()
                          if len(value) > 1},
        "additional_conflicts": [list(edge) for edge in sorted(effective_edges - base_edges)],
        "self_forbidden": sorted(edge[0] for edge in effective_edges if edge[0] == edge[1]),
        "constraint_rule": "one binary per active representative; x_u+x_v<=1 for every auxiliary edge; merged representatives select all mapped originals",
    }


def _pool_records(columns, auxiliary, graph):
    """Express inherited columns in the current graph's representative IDs.

    Same-color branching filters inherited columns but does not rewrite their
    stored vertices. Their associated pricing problem still owns the parent
    graph, so it can expand a representative eliminated by a later merge.
    """
    stored, originals, canonical, unrepresentable = set(), set(), set(), set()
    active_mapping = {int(key): set(value)
                      for key, value in graph["original_vertex_mapping"].items()}
    unknown_originals = set()
    for column in columns:
        stored.add(tuple(sorted(vertex.id for vertex in column.vertex_list)))
        source_problem = getattr(column, "associated_pricing_problem", None)
        source_graph = getattr(source_problem, "auxiliary_graph", auxiliary)
        original_ids = set()
        for vertex in column.vertex_list:
            owner = auxiliary if vertex.id in auxiliary.vertices_map else source_graph
            original_ids.update(original.id for original in owner.get_original_vertices(vertex))
        original_signature = tuple(sorted(original_ids))
        originals.add(original_signature)
        unknown_originals.update(original_ids - set(auxiliary.graph.vertex_map))
        representatives = tuple(sorted(identifier for identifier, represented in active_mapping.items()
                                       if represented <= original_ids))
        covered = set().union(*(active_mapping[identifier] for identifier in representatives))
        if covered == original_ids:
            canonical.add(representatives)
        else:
            # Such columns cannot equal any current pricing candidate, but the
            # complete original pool is preserved rather than silently lost.
            unrepresentable.add(original_signature)
    return (sorted(canonical), sorted(originals), sorted(stored),
            sorted(unrepresentable), sorted(unknown_originals))


def _phase(master, context):
    if context.get("phase") is not None:
        return str(context["phase"])
    if master is None:
        return "unspecified"
    if float(master.T.Obj) == 0.0:
        return "I"
    artificial = [variable for columns in master.varMap.values()
                  for column, variable in columns.items() if column.is_artificial_column]
    if artificial and any(float(variable.UB) > 0.0 for variable in artificial):
        return "II_penalized_initial"
    return "II"


def _raw_duals(master, dual):
    if master is None:
        return {"available": False, "reason": "No master rows supplied; effective pricing duals retained"}
    return {
        "available": True,
        "partition": {str(key): float(row.Pi) for key, row
                      in master.each_partition_colored_once_constraint.items()},
        "vertex_makespan": {str(key): float(row.Pi) for key, row
                            in master.vertex_makespan_constraints.items()},
        "vehicle_makespan": {str(key): float(row.Pi) for key, row
                             in master.vehicle_makespan_constraints.items()},
        "charger": float(master.charger_capacity_constraint.Pi)
        if master.charger_capacity_constraint is not None else 0.0,
        "effective_makespan_rule": "vertex row dual + corresponding vehicle row dual",
    }


def _encoding(heuristic):
    ids, weights, adjacency, forbidden, j_matrix, h_vector = heuristic._build_ising_model()
    index = {vertex: position for position, vertex in enumerate(ids)}
    penalty = max(1.0, max((max(weight, 0.0) for weight in weights.values()), default=0.0)) + heuristic.penalty_margin
    qubo = np.diag([-weights[vertex] + (penalty if vertex in forbidden else 0.0)
                    for vertex in ids]).astype(np.float64)
    raw_j = np.zeros((len(ids), len(ids)), dtype=np.float64)
    raw_h = np.array([weights[vertex] / 2.0 for vertex in ids], dtype=np.float64)
    edges = [(u, v) for u in ids for v in sorted(adjacency[u]) if u < v]
    for u, v in edges:
        i, k = index[u], index[v]
        qubo[i, k] = qubo[k, i] = penalty / 2.0
        raw_j[i, k] = raw_j[k, i] = -penalty / 4.0
        raw_h[i] -= penalty / 4.0
        raw_h[k] -= penalty / 4.0
    for vertex in forbidden:
        raw_h[index[vertex]] -= penalty / 2.0
    scale = max(float(np.abs(raw_j).max()) if raw_j.size else 0.0,
                float(np.abs(raw_h).max()) if raw_h.size else 0.0, 1.0)
    if not heuristic.normalize_ising:
        scale = 1.0
    return {
        "vertex_ids": ids, "Q": qubo.tolist(), "J": j_matrix.toarray().tolist(),
        "h": h_vector.tolist(), "raw_J": raw_j.tolist(), "raw_h": raw_h.tolist(),
        "normalization_scale": scale, "penalty": penalty, "self_forbidden": sorted(forbidden),
        "qubo_convention": "min x.T @ Q @ x; symmetric Q with P/2 off diagonal",
        "ising_convention": "min H=-0.5*s.T@J@s-h.T@s; x=(1+s)/2",
        "qubo_ising_conversion_constant": -sum(weights.values()) / 2.0 + penalty * len(edges) / 4.0 + penalty * len(forbidden) / 2.0,
        "energy_relation": "qubo_energy=normalization_scale*normalized_ising_energy+qubo_ising_conversion_constant",
        "classical_dtype": "float64", "device_encoding": "Recorded separately in each CIM replay; device precision quantization is not applied here",
    }


def make_snapshot(pricing_problem, column_pool=None, heuristic=None, master=None, context=None):
    """Capture an already updated PricingProblem without solving or sampling."""
    started = time.perf_counter()
    context = dict(getattr(pricing_problem, "snapshot_context", {}) if context is None else context)
    auxiliary = pricing_problem.auxiliary_graph
    if heuristic is None:
        from cg.pricing.qaia_exact_pricing_solver import QAIAPricingSolver
        heuristic = QAIAPricingSolver(auxiliary, pricing_problem, provider="greedy")
    elif hasattr(heuristic, "qaia_solver"):
        heuristic = heuristic.qaia_solver
    graph = _graph_record(auxiliary)
    columns = [] if column_pool is None else column_pool.columns
    real_columns = [column for column in columns if not column.is_artificial_column]
    pool_signatures, pool_originals, pool_stored, pool_unrepresentable, pool_unknown = _pool_records(
        real_columns, auxiliary, graph)
    config = {key: getattr(heuristic, key) for key in (
        "provider", "algorithm", "n_iter", "batch_size", "backend", "penalty_margin",
        "epsilon", "max_columns", "random_seed", "normalize_ising", "algorithm_kwargs")}
    config["environment"] = {key: value for key, value in sorted(os.environ.items())
                             if key.startswith(("QAIA_", "BPC_", "EXACT_", "CIM_"))}
    phase = _phase(master, context)
    missing = []
    if phase == "unspecified":
        missing.append("phase")
    if "partition" not in pricing_problem.dual:
        missing.append("partition_duals")
    if column_pool is None:
        missing.append("existing_column_pool")
    if pool_unknown:
        missing.append("existing_column_pool_original_mapping")
    payload = {
        "schema": SCHEMA, "graph": graph, "phase": phase,
        "completeness": {"independently_replayable": not missing,
                         "missing": missing},
        "dual": _json_value(pricing_problem.dual),
        "raw_master_duals": _raw_duals(master, pricing_problem.dual),
        "weights": {str(vertex): float(auxiliary.weight_v[vertex])
                    for vertex in sorted(auxiliary.vertices_map)},
        "reduced_cost": {"real_column_objective": 0.0,
                         "constant": -float(pricing_problem.dual.get("charger", 0.0)),
                         "rule": "rc=0-charger_dual-sum_original(partition_dual-end_time*effective_makespan_dual)",
                         "negative_threshold": -float(heuristic.epsilon)},
        "branch_constraints": _branch_record(auxiliary, graph),
        "pool_signatures": [list(signature) for signature in pool_signatures],
        "pool_original_signatures": [list(signature) for signature in pool_originals],
        "pool_stored_signatures": [list(signature) for signature in pool_stored],
        "pool_unrepresentable_original_signatures": [list(signature) for signature in pool_unrepresentable],
        "pool_signature_rule": "Expand each inherited column through its owning pricing graph, then map complete original groups onto the current active representatives; unreachable original sets are preserved separately",
        "pool_artificial_signatures": [sorted(vertex.id for vertex in column.vertex_list)
                                       for column in columns if column.is_artificial_column],
        "encoding": _encoding(heuristic), "config": _json_value(config),
        "provenance": {"captured_at_utc": datetime.now(timezone.utc).isoformat(),
                       "problem_name": pricing_problem.name, "context": _json_value(context),
                       "version": _versions(), "master_supplied": master is not None},
        "deduplication": {"rule": "Exact canonical task hash including phase, effective/raw duals, graph/mapping, encoding and existing real-column pool; seed, provider, CG iteration and source path excluded", "cross_phase": "distinct"},
    }
    payload["task_hash"] = task_hash(payload)
    payload["provenance"]["capture_seconds"] = time.perf_counter() - started
    # Fail immediately rather than quietly saving non-finite duals or matrices.
    _canonical(payload)
    return payload


def save_snapshot(payload, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"snapshot_{payload['task_hash']}.json"
    if not path.exists():
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(_json_value(payload), ensure_ascii=False,
                                   indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
        temp.replace(path)
    return path


def load_snapshot(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if payload.get("schema") != SCHEMA:
        raise ValueError(f"Unsupported pricing snapshot schema: {payload.get('schema')}")
    if payload.get("task_hash") != task_hash(payload):
        raise ValueError("Pricing snapshot task hash mismatch")
    return payload


def _numeric_keys(value):
    if not isinstance(value, dict):
        return value
    return {int(key) if key.lstrip("-").isdigit() else key: _numeric_keys(item)
            for key, item in value.items()}


def restore_snapshot(payload):
    """Rebuild graph/duals from JSON with no live master or Gurobi model."""
    if isinstance(payload, (str, Path)):
        payload = load_snapshot(payload)
    if payload.get("schema") != SCHEMA or payload.get("task_hash") != task_hash(payload):
        raise ValueError("Invalid pricing snapshot schema/hash")
    graph_data = payload["graph"]
    # Deserialization must not increment Vertex's global ID generator.
    vertices = {}
    for record in graph_data["original_vertices"] + graph_data["active_vertices"]:
        if record["id"] not in vertices:
            vertex = Vertex.__new__(Vertex)
            vertex.id = record["id"]
            vertex.end_time = record["end_time"]
            vertices[vertex.id] = vertex
    partitions = {record["id"]: Partition(record["id"], [vertices[vertex]
                   for vertex in record["vertex_ids"]]) for record in graph_data["partitions"]}
    for record in graph_data["original_vertices"] + graph_data["active_vertices"]:
        if record["partition_id"] is not None:
            vertices[record["id"]].set_associated_partition(partitions[record["partition_id"]])
    original_graph = Graph(
        [Edge(vertices[u], vertices[v]) for u, v in graph_data["original_edges"]],
        [vertices[record["id"]] for record in graph_data["original_vertices"]],
        [partitions[key] for key in sorted(partitions)])
    active = {record["id"]: vertices[record["id"]] for record in graph_data["active_vertices"]}
    merged = {vertices[int(key)]: [vertices[vertex] for vertex in originals]
              for key, originals in graph_data["original_vertex_mapping"].items()
              if originals != [int(key)]}
    auxiliary = AuxiliaryGraph(original_graph, active,
        [Edge(vertices[u], vertices[v]) for u, v in graph_data["auxiliary_edges"]], merged)
    auxiliary.weight_v = {int(key): float(value) for key, value in payload["weights"].items()}
    problem = PricingProblem(auxiliary, payload["provenance"]["problem_name"],
                             _numeric_keys(payload["dual"]))
    problem.snapshot_context = dict(payload["provenance"].get("context", {}), phase=payload["phase"])
    # Recompute weights independently from original duals, including merged vertices.
    recomputed = auxiliary.copy()
    recomputed.update_weightf(problem.dual)
    for vertex, weight in auxiliary.weight_v.items():
        if not np.isclose(weight, recomputed.weight_v[vertex], rtol=0.0, atol=1e-9):
            raise ValueError(f"Snapshot weight disagrees with original dual at vertex {vertex}")
    return auxiliary, problem


class SnapshotCollector:
    def __init__(self, directory, limit=0, root_only=True):
        if limit < 0:
            raise ValueError("Snapshot limit must be nonnegative")
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.limit = int(limit)
        self.root_only = bool(root_only)
        self.hashes = {load_snapshot(path)["task_hash"]
                       for path in self.directory.glob("snapshot_*.json")}
        self.events = self.directory / "capture_events.jsonl"

    @classmethod
    def from_environment(cls):
        directory = os.getenv("PRICING_SNAPSHOT_DIR")
        if not directory:
            return None
        return cls(directory, int(os.getenv("PRICING_SNAPSHOT_LIMIT", "0")),
                   os.getenv("PRICING_SNAPSHOT_ROOT_ONLY", "1") == "1")

    def capture(self, pricing_problem, column_pool=None, heuristic=None, master=None, context=None):
        if self.limit and len(self.hashes) >= self.limit:
            raise SnapshotLimitReached(self.directory, len(self.hashes))
        payload = make_snapshot(pricing_problem, column_pool, heuristic, master, context)
        capture_context = payload["provenance"]["context"]
        explicit_root = capture_context.get("is_root")
        branches = payload["branch_constraints"]
        inferred_root = not (branches["removed_original_vertices"] or branches["merged_groups"]
                             or branches["additional_conflicts"])
        is_root = bool(explicit_root) if explicit_root is not None else inferred_root
        payload["provenance"]["root_classification"] = "explicit" if explicit_root is not None else "inferred_from_effective_constraints"
        if self.root_only and not is_root:
            return None
        duplicate = payload["task_hash"] in self.hashes
        path = save_snapshot(payload, self.directory)
        self.hashes.add(payload["task_hash"])
        with self.events.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"task_hash": payload["task_hash"], "path": str(path),
                                    "duplicate": duplicate, "phase": payload["phase"],
                                    "context": capture_context,
                                    "captured_at_utc": payload["provenance"]["captured_at_utc"]},
                                   ensure_ascii=False) + "\n")
        if self.limit and len(self.hashes) >= self.limit:
            raise SnapshotLimitReached(self.directory, len(self.hashes), path)
        return path
