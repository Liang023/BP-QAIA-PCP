"""Offline, hand-checkable tests for pricing snapshots and sampler comparisons.

No test submits a CIM task.  The four-vertex instance is fully enumerable;
expected reduced costs come directly from the original master duals.
"""
from itertools import product
from types import SimpleNamespace
import numpy as np
import pytest

from cg.column_independent_set import ColumnIndependentSet
from cg.column_pool import ColumnPool
from cg.pricing.pricing_problem import PricingProblem
from cg.pricing.qaia_exact_pricing_solver import QAIAPricingSolver
from model.a_graph import AuxiliaryGraph
from model.edge import Edge
from model.graph import Graph
from model.partition import Partition
from model.vertex import Vertex


def small_problem(monkeypatch, *, self_loop=True):
    monkeypatch.setattr(Vertex, "_next_vertex_id", 0)
    vertices = [Vertex(t) for t in (1, 2, 3, 4)]
    partitions = [Partition(0, vertices[:2]), Partition(1, vertices[2:3]),
                  Partition(2, vertices[3:])]
    for partition in partitions:
        for vertex in partition.vertex_list:
            vertex.set_associated_partition(partition)
    edges = [Edge(vertices[0], vertices[2])]
    if self_loop:
        edges.append(Edge(vertices[3], vertices[3]))
    graph = AuxiliaryGraph(Graph(edges, vertices, partitions),
                           {v.id: v for v in vertices})
    problem = PricingProblem(graph, "enumerable", {})
    # w_v = pi_partition - mu_v * end_time = (3, 1, 2, 5).
    problem.update_pricing_problem({"partition": {0: 3., 1: 2., 2: 5.},
                                    "makespan": {1: 1.}, "charger": -1.})
    solver = QAIAPricingSolver(graph, problem, provider="greedy",
                              n_iter=20, batch_size=5, max_columns=1,
                              random_seed=7, normalize_ising=False)
    return graph, problem, solver


def test_enumerated_qubo_ising_equivalence_and_forbidden_vertex(monkeypatch):
    graph, problem, solver = small_problem(monkeypatch)
    ids, weights, adjacency, forbidden, matrix, field = solver._build_ising_model()
    assert ids == [0, 1, 2, 3]
    assert weights == {0: 3., 1: 1., 2: 2., 3: 5.}
    assert forbidden == {3}
    assert adjacency == {0: {1, 2}, 1: {0}, 2: {0}, 3: set()}
    penalty = 6.
    offsets = []
    states = []
    for bits in product((0, 1), repeat=4):
        x = np.asarray(bits)
        spin = 2 * x - 1
        qubo = -sum(weights[v] * x[i] for i, v in enumerate(ids))
        qubo += penalty * (x[0] * x[1] + x[0] * x[2] + x[3])
        ising = -.5 * float(spin @ matrix @ spin) - float(field @ spin)
        offsets.append(qubo - ising)
        legal = not (x[0] * x[1] or x[0] * x[2] or x[3])
        states.append((float(qubo), legal))
    assert np.max(offsets) - np.min(offsets) < 1e-12
    minimum = min(energy for energy, _ in states)
    assert all(legal for energy, legal in states if energy == minimum)


def test_hand_checked_raw_and_repaired_metrics(monkeypatch):
    from cg.pricing.pricing_replay import evaluate_samples
    graph, problem, solver = small_problem(monkeypatch)
    samples = np.asarray([[1, 0, 0, 0, 0],
                          [1, 1, 0, 0, 1],
                          [1, 1, 0, 0, 1],
                          [1, 0, 0, 1, 0]], dtype=np.int8)
    result = evaluate_samples(problem, solver, samples,
                              excluded={(0,)}, max_columns=1)
    metrics = result["metrics"]
    expected = dict(raw_sample_count=5, raw_unique_count=4,
                    raw_legal_sample_count=3, repaired_unique_legal_count=2,
                    unique_negative_reduced_cost_count=2,
                    effective_new_column_count=1, returned_column_count=1,
                    best_legal_reduced_cost=-2.)
    for key, value in expected.items():
        assert metrics[key] == value, key
    records = result["per_sample"]
    assert [row["raw"]["selected"] for row in records] == [
        [0, 1, 2, 3], [1, 2], [], [3], [1, 2]]
    assert [row["raw"]["conflict_count"] for row in records] == [3, 0, 0, 1, 0]
    assert [row["raw"]["legal"] for row in records] == [False, True, True, False, True]
    assert [row["raw"]["reduced_cost"] for row in records] == [None, -2., 1., None, -2.]
    assert [row["repaired"]["selected"] for row in records] == [[0], [1, 2], [0], [0], [1, 2]]
    assert [row["repaired"]["modification_count"] for row in records] == [3, 0, 1, 2, 0]
    assert all(row["repaired"]["legal"] for row in records)
    assert all(row["repaired"]["reduced_cost"] == -2. for row in records)
    assert metrics["ratios"]["raw_legality"] == dict(numerator=3, denominator=5, value=.6)
    assert metrics["ratios"]["negative_among_unique_repaired"] == dict(
        numerator=2, denominator=2, value=1.)
    assert metrics["ratios"]["new_among_unique_negative"] == dict(
        numerator=1, denominator=2, value=.5)


def test_empty_output_keeps_zero_counts_and_missing_best(monkeypatch):
    from cg.pricing.pricing_replay import evaluate_samples
    graph, problem, solver = small_problem(monkeypatch)
    result = evaluate_samples(problem, solver, np.empty((4, 0), dtype=np.int8))
    assert result["per_sample"] == []
    assert result["metrics"]["raw_sample_count"] == 0
    assert result["metrics"]["effective_new_column_count"] == 0
    assert result["metrics"]["best_legal_reduced_cost"] is None


def test_snapshot_roundtrip_preserves_branch_graph_and_original_duals(monkeypatch, tmp_path):
    import json
    from cg.pricing.pricing_snapshot import make_snapshot, load_snapshot, restore_snapshot
    graph, problem, solver = small_problem(monkeypatch, self_loop=False)
    # The nonadjacent vertices 1 and 2 are represented by one decision bit.
    graph.same_color(graph.vertices_map[1], graph.vertices_map[2])
    merged_id = next(iter(graph.merged_vertices_map)).id
    graph.different_color(graph.vertices_map[merged_id], graph.vertices_map[3])
    problem.update_pricing_problem(problem.dual)
    pool = ColumnPool()
    pool.addColumn(ColumnIndependentSet([graph.vertices_map[merged_id]], problem,
                                        False, "fixture"))
    payload = make_snapshot(problem, pool, solver,
                            context={"phase": "II", "node_depth": 1})
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    loaded = load_snapshot(path)
    restored_graph, restored_problem = restore_snapshot(loaded)
    assert restored_problem.dual == problem.dual
    assert restored_graph.weight_v == {v: graph.weight_v[v] for v in graph.vertices_map}
    assert sorted(restored_graph.vertices_map) == [0, 3, merged_id]
    assert sorted(v.id for v in restored_graph.get_original_vertices(
        restored_graph.vertices_map[merged_id])) == [1, 2]
    assert {tuple(sorted((edge.source.id, edge.target.id)))
            for edge in restored_graph.auxiliary_edges} == {(0, merged_id), (3, merged_id)}
    from cg.pricing.pricing_replay import evaluate_samples
    restored_solver = QAIAPricingSolver(restored_graph, restored_problem,
                                       provider="greedy", normalize_ising=False)
    # Ordering is 0, 3, merged_id; selecting only the representative scores
    # 1 - ((3 - 1*2) + 2) = -2, from expanded original dual coefficients.
    result = evaluate_samples(restored_problem, restored_solver,
                              np.asarray([[0], [0], [1]], dtype=np.int8))
    assert result["per_sample"][0]["raw"]["reduced_cost"] == -2.
    assert loaded["pool_signatures"] == [[merged_id]]


def test_random_sampling_reuses_greedy_seeded_sampler():
    first = QAIAPricingSolver._random_samples(8, 20, 123)
    second = QAIAPricingSolver._random_samples(8, 20, 123)
    assert first.shape == (8, 20)
    assert np.array_equal(first, second)
    assert np.isin(first, [0, 1]).all()


def test_snapshot_encoding_and_semantic_deduplication(monkeypatch):
    from cg.pricing.pricing_snapshot import make_snapshot
    graph, problem, solver = small_problem(monkeypatch)
    pool = ColumnPool()
    payload = make_snapshot(problem, pool, solver, context={"phase": "I", "is_root": True})
    solver.random_seed = 991
    solver.provider = "qaia"
    same = make_snapshot(problem, pool, solver, context={"phase": "I", "is_root": True})
    assert same["task_hash"] == payload["task_hash"]
    next_phase = make_snapshot(problem, pool, solver, context={"phase": "II", "is_root": True})
    assert next_phase["task_hash"] != payload["task_hash"]
    pool.addColumn(ColumnIndependentSet([graph.vertices_map[0]], problem, False, "fixture"))
    different_pool = make_snapshot(problem, pool, solver, context={"phase": "I", "is_root": True})
    assert different_pool["task_hash"] != payload["task_hash"]
    encoding = payload["encoding"]
    qubo = np.asarray(encoding["Q"])
    j, h = np.asarray(encoding["J"]), np.asarray(encoding["h"])
    for bits in product((0, 1), repeat=4):
        x = np.asarray(bits)
        spin = 2*x - 1
        energy = -.5 * spin @ j @ spin - h @ spin
        assert float(x @ qubo @ x) == pytest.approx(
            encoding["normalization_scale"] * energy + encoding["qubo_ising_conversion_constant"])


def test_snapshot_limit_stops_at_requested_unique_count(monkeypatch, tmp_path):
    from cg.pricing.pricing_snapshot import SnapshotCollector, SnapshotLimitReached
    graph, problem, solver = small_problem(monkeypatch)
    collector = SnapshotCollector(tmp_path, limit=1)
    with pytest.raises(SnapshotLimitReached) as error:
        collector.capture(problem, ColumnPool(), solver,
                          context={"phase": "II", "is_root": True})
    assert error.value.count == 1
    assert len(list(tmp_path.glob("snapshot_*.json"))) == 1
    with pytest.raises(SnapshotLimitReached):
        collector.capture(problem, ColumnPool(), solver,
                          context={"phase": "II", "is_root": True})
    assert len(list(tmp_path.glob("snapshot_*.json"))) == 1


def test_exact_replay_matches_enumerated_original_pricing(monkeypatch, tmp_path):
    from cg.pricing.pricing_snapshot import make_snapshot, save_snapshot
    from cg.pricing.pricing_replay import replay_task
    graph, problem, solver = small_problem(monkeypatch)
    path = save_snapshot(make_snapshot(problem, ColumnPool(), solver,
                                      context={"phase": "II", "is_root": True}), tmp_path)
    result = replay_task(path, "exact", sample_limit=5, max_columns=2, time_limit=10)
    assert result["status"] == "optimal", result.get("error")
    exact = result["exact"]
    assert exact["status"] == "optimal"
    assert exact["optimality_proven"] is True
    assert exact["maximum_weight"] == pytest.approx(3.)
    assert exact["weight_upper_bound"] == pytest.approx(3.)
    assert exact["optimal_reduced_cost"] == pytest.approx(-2.)
    assert exact["reduced_cost_lower_bound"] == pytest.approx(-2.)


def test_sa_reproducibility_and_iteration_budget(monkeypatch):
    import time
    from cg.pricing.pricing_replay import simulated_annealing
    graph, problem, solver = small_problem(monkeypatch)
    ids, weights, adjacency, forbidden, matrix, field = solver._build_ising_model()
    args = dict(sample_limit=5, n_iter=20, seed=10, deadline=time.perf_counter()+10)
    first, settings = simulated_annealing(matrix, field, **args)
    second, _ = simulated_annealing(matrix, field, **args)
    assert np.array_equal(first, second)
    assert first.shape == (4, 5)
    assert settings["temperature_schedule"] == "geometric"
    assert settings["completed_sweeps"] == 20
    assert settings["completed_proposals"] == 400
    assert settings["timed_out"] is False
    expired, expired_settings = simulated_annealing(
        matrix, field, sample_limit=5, n_iter=20, seed=10,
        deadline=time.perf_counter()-1)
    assert expired.shape == (4, 5)
    assert expired_settings["timed_out"] is True
    assert expired_settings["completed_proposals"] == 0


def test_invalid_raw_output_is_retained(monkeypatch):
    from cg.pricing.pricing_replay import evaluate_samples
    graph, problem, solver = small_problem(monkeypatch)
    samples = np.array([[np.nan], [1.], [0.], [0.]])
    result = evaluate_samples(problem, solver, samples)
    assert result["metrics"]["raw_sample_count"] == 1
    assert result["metrics"]["invalid_sample_count"] == 1
    assert result["per_sample"][0]["status"] == "invalid_output"
    assert result["per_sample"][0]["repaired"] is None
    assert result["metrics"]["best_legal_reduced_cost"] is None


def test_cim_precision_input_and_zero_retry_policy_offline(monkeypatch, tmp_path):
    """Use the installed reducer; replace the only cloud boundary with a fake."""
    import json
    import kaiwu as kw
    from cg.pricing.cim_worker import prepare_model, solve_request
    calls = {"solve": 0, "submit": 0}
    instances = []

    class OfflineCIM(kw.core.OptimizerBase):
        def __init__(self, **kwargs):
            super().__init__()
            self._runner = SimpleNamespace(wuyue_client=SimpleNamespace(
                config=SimpleNamespace(auto_retry=True, max_retry_times=3)))
            instances.append(self)

        def _create_task(self, *args, **kwargs):
            calls["submit"] += 1
            return "offline-task"

        def solve(self, matrix):
            calls["solve"] += 1
            self._create_task(matrix)
            self.set_matrix(matrix)
            candidates = np.asarray(list(product((-1, 1), repeat=len(matrix))), dtype=np.int8)
            energies = np.asarray(kw.common.hamiltonian(matrix, candidates)).reshape(-1)
            ordered = np.argsort(energies)
            # Worst starts arrive first; later low-energy outputs must not
            # replace them when the common sample cap is two.
            return candidates[np.r_[ordered[-2:], ordered[:2]]]

    boundary = SimpleNamespace(core=kw.core, qubo=kw.qubo, conversion=kw.conversion,
        common=kw.common, __version__=kw.__version__,
        cim=SimpleNamespace(CIMOptimizer=OfflineCIM, PrecisionReducer=kw.cim.PrecisionReducer))
    monkeypatch.setenv("ECLOUD_ACCESS_KEY", "offline-key")
    monkeypatch.setenv("ECLOUD_SECRET_KEY", "offline-secret")
    monkeypatch.setattr(kw.common.CheckpointManager, "save_dir", str(tmp_path))
    request = dict(ids=[0, 1], weights=[1.23, 1.], edges=[[0, 1]], forbidden=[],
        penalty=3., task="offline", options=dict(max_bits=1000, precision=8, device_id="mock"),
        replay_context=dict(strict_no_retry=True, sample_limit=2))
    samples = solve_request(request, tmp_path, boundary)
    assert samples.shape == (2, 2)
    assert np.isin(samples, [0, 1]).all()
    assert calls == {"solve": 1, "submit": 1}
    retry_config = instances[0]._runner.wuyue_client.config
    assert retry_config.auto_retry is False and retry_config.max_retry_times == 0
    encoding = json.loads((tmp_path / "encoding_metadata.json").read_text())
    assert encoding["actual_device_input_saved"] is True
    assert encoding["retry_policy"] == dict(auto_retry=False, max_retry_times=0, max_submissions=1)
    assert encoding["submission_attempts"] == 1
    assert encoding["raw_received_sample_count"] == 4
    assert encoding["evaluated_sample_count"] == 2
    original = np.load(tmp_path / "pre_quantization_matrix.npy", allow_pickle=False)
    device = np.load(tmp_path / "device_input_matrix.npy", allow_pickle=False)
    assert original.shape == device.shape
    assert not np.array_equal(original, device)
    assert np.isfinite(device).all()
    assert (tmp_path / "raw_spins.npy").exists()
    raw = np.load(tmp_path / "raw_spins.npy", allow_pickle=False)
    assert raw.shape[0] == 2
    device_raw = np.load(tmp_path / "device_output_spins.npy", allow_pickle=False)
    assert device_raw.shape[0] == 4
    device_energies = np.asarray(kw.common.hamiltonian(device, device_raw)).reshape(-1)
    assert min(device_energies[:2]) > min(device_energies[2:])
    matrix, variables = prepare_model(request, boundary)
    full_energies = np.asarray(kw.common.hamiltonian(matrix, raw)).reshape(-1)
    assert sorted(encoding["decoded_sample_order"]) == [0, 1]
    expected_rows = [kw.core.get_sol_dict(raw[i], variables)
                     for i in np.argsort(full_energies[:2])]
    expected_samples = np.asarray([[row.get(f"x_{v}", 0) for row in expected_rows]
                                   for v in request["ids"]], dtype=np.int8)
    assert np.array_equal(samples, expected_samples)
    # Exercise the guarded submission path directly: a second attempt must
    # fail before the offline submission boundary is called again.
    with pytest.raises(RuntimeError, match="Additional CIM submission blocked"):
        instances[0]._create_task(device)
    assert calls["submit"] == 1


def test_snapshot_inherited_original_column_maps_to_merged_pool_signature(monkeypatch):
    from cg.pricing.pricing_snapshot import make_snapshot, restore_snapshot
    from cg.pricing.pricing_replay import evaluate_samples
    graph, problem, solver = small_problem(monkeypatch, self_loop=False)
    pool = ColumnPool()
    # The parent node column retains original objects after the active graph
    # merges its two representatives into one decision variable.
    pool.addColumn(ColumnIndependentSet([graph.vertices_map[1], graph.vertices_map[2]],
                                        problem, False, "inherited fixture"))
    graph.same_color(graph.vertices_map[1], graph.vertices_map[2])
    merged_id = next(iter(graph.merged_vertices_map)).id
    graph.different_color(graph.vertices_map[merged_id], graph.vertices_map[3])
    problem.update_pricing_problem(problem.dual)
    payload = make_snapshot(problem, pool, solver, context={"phase": "II", "is_root": False})
    assert payload["pool_stored_signatures"] == [[1, 2]]
    assert payload["pool_original_signatures"] == [[1, 2]]
    assert payload["pool_signatures"] == [[merged_id]]
    restored_graph, restored_problem = restore_snapshot(payload)
    restored_solver = QAIAPricingSolver(restored_graph, restored_problem,
                                       provider="greedy", normalize_ising=False)
    result = evaluate_samples(restored_problem, restored_solver,
        np.asarray([[0], [0], [1]], dtype=np.int8), excluded=payload["pool_signatures"])
    assert result["per_sample"][0]["repaired"]["selected"] == [merged_id]
    assert result["metrics"]["unique_negative_reduced_cost_count"] == 1
    assert result["metrics"]["effective_new_column_count"] == 0
    assert result["per_sample"][0]["already_in_pool"] is True


def test_cim_timeout_retains_submitted_device_artifacts(monkeypatch, tmp_path):
    import json
    from cg.pricing.cim_backend import CIMBackend
    from cg.pricing.pricing_snapshot import make_snapshot, save_snapshot
    from cg.pricing.pricing_replay import replay_task
    graph, problem, solver = small_problem(monkeypatch)
    path = save_snapshot(make_snapshot(problem, ColumnPool(), solver,
                                      context={"phase": "II", "is_root": True}), tmp_path)
    directory = tmp_path / "offline_timed_out_cloud"
    directory.mkdir()
    encoding = dict(actual_device_input_saved=True, submission_attempts=1,
                    encoding_seconds=.02, device_call_seconds=.15,
                    retry_policy=dict(auto_retry=False, max_retry_times=0, max_submissions=1))
    (directory / "encoding_metadata.json").write_text(json.dumps(encoding), encoding="utf-8")
    np.save(directory / "device_input_matrix.npy", np.zeros((5, 5)))
    (directory / "cloud_timing.json").write_text(
        json.dumps(dict(cloud_call_seconds=.15)), encoding="utf-8")

    def timed_out_sample(self, *args, **kwargs):
        self.metrics["requests"] += 1
        self.metrics["tasks"].append(dict(task="offline-timeout", directory=str(directory),
                                           status="timeout", seconds=.17))
        raise TimeoutError("offline simulated cloud wait timeout")

    monkeypatch.setattr(CIMBackend, "sample", timed_out_sample)
    result = replay_task(path, "cim", cim_mode="new", sample_limit=2, time_limit=1)
    assert result["status"] == "time_limit"
    assert result["batch_identity"] == "offline-timeout"
    assert result["backend_request_attempt_count"] == 1
    assert result["actual_cloud_submission_count"] == 1
    assert result["metrics"]["raw_sample_count"] == 0
    assert result["encoding"]["quantization"]["actual_device_input_saved"] is True
    assert result["encoding"]["quantization"]["device_call_seconds"] == .15
    assert result["timing"]["device_encoding_seconds"] == .02
    assert result["timing"]["device_call_seconds"] == .15
