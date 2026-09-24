"""Correctness checks for incumbent neighborhoods and equivalent branching."""
import itertools
import random

import pytest

pytest.importorskip("gurobipy")
from bpc.branch_creator import BranchCreator
from cg import budget_clock
from cg.column_independent_set import ColumnIndependentSet
from cg.column_pool import ColumnPool
from cg.primal_completion import complete_root_pool
from cg.primal_neighborhood import improve_incumbent
from ev.ev_to_pcp import ev_json_to_instance
from model.a_graph import AuxiliaryGraph
from validation.ev_solution import validate_schedule


def instance():
    data = dict(num_vehicles=4, num_chargers=2, time_horizon=8,
        vehicles=[dict(id=i, duration=2, candidates=[
            dict(candidate_id=j, start=2*j, end=2*j+2) for j in range(4)])
            for i in range(4)])
    return ev_json_to_instance(data)


def col(vertices):
    return ColumnIndependentSet(vertices, None, False, "test")


def test_neighborhood_improves_and_preserves_fixed_assignments():
    inst = instance()
    graph = inst.graph
    v = [p.vertex_list for p in graph.partitions]
    incumbent = {col([v[0][0], v[1][1], v[2][2]]): 1.0, col([v[3][0]]): 1.0}
    original = AuxiliaryGraph(graph, graph.vertex_map)
    candidates = []
    def accept(sol, objective):
        checked = validate_schedule(sol, original, graph, 2, objective)
        assert checked["makespan"] < 6
        # The first vehicle remains fixed on the first charger.
        assert v[0][0] in next(iter(sol)).vertex_list
        candidates.append(objective)
    result = improve_incumbent(graph, 2, incumbent, 6, budget_clock.now()+5,
                               2, 2, 0, accept)
    assert candidates and min(candidates) == 4
    assert result["free_vehicles"] == 2 and result["variables"] > 0


def test_neighborhood_exhaustion_does_not_claim_global_infeasible():
    inst = instance()
    v = [p.vertex_list for p in inst.graph.partitions]
    incumbent = {col([v[0][0], v[1][1]]): 1.0, col([v[2][0], v[3][1]]): 1.0}
    # No one-vehicle neighborhood can release both last-finishing vehicles.
    result = improve_incumbent(inst.graph, 2, incumbent, 4, budget_clock.now()+5,
                               2, 1, 0, lambda *_: pytest.fail("Unexpected candidate"))
    assert result["status"] == "skipped"


def test_best_injection_preserves_best_schedule_with_fewer_columns():
    inst = instance()
    args = (inst.graph, 2, {}, ColumnPool(), None)
    best, solutions, _ = complete_root_pool(*args, budget_clock.now()+5, 20, 3)
    all_cols, all_solutions, _ = complete_root_pool(
        *args, budget_clock.now()+5, 20, 3, injection="all")
    value = lambda s: max(v.end_time for c in s for v in c.vertex_list)
    assert min(map(value, solutions)) == min(map(value, all_solutions))
    assert len(best) <= 2 and len(best) < len(all_cols)


def test_global_neighborhood_closes_bound_without_injecting_node_columns(monkeypatch):
    from bpc.branch_and_price import BranchAndPrice, BoundClosed
    from cg.anytime import IncumbentRecorder
    monkeypatch.setenv("BPC_NEIGHBORHOOD", "1")
    monkeypatch.setenv("BPC_NEIGHBORHOOD_VEHICLES", "2")
    inst = instance()
    bp = BranchAndPrice(inst.graph, 2, 60, use_qaia=False)
    root = bp.generate_root_node()
    bp.current_node = root
    bp._original_a_graph = root.a_graph
    start = budget_clock.now()
    bp.deadline = start + 60
    bp.recorder = IncumbentRecorder(start, bp.deadline)
    bp.problem_lower_bound = 4
    v = [p.vertex_list for p in inst.graph.partitions]
    bp.best_solution = {col([v[0][0], v[1][1], v[2][2]]): 1.0, col([v[3][0]]): 1.0}
    bp.best_objective = 6
    initial_columns = list(root.column_pool.columns)
    with pytest.raises(BoundClosed):
        bp._maybe_neighborhood(bp.deadline)
    assert bp.best_objective == bp.problem_lower_bound == 4
    assert root.column_pool.columns == initial_columns
    assert bp.neighborhood_metrics["improvements"] == 1
    assert bp.neighborhood_metrics["max_variables"] > 0
    assert bp.neighborhood_metrics["seconds"] > 0
    assert bp.recorder.fields()["incumbent_history"][-1]["source"] == "primal_neighborhood"


def reference_pair(brancher):
    best, pair = 0.0, None
    vertices = list(brancher.a_graph.vertices_map.values())
    for u, v in itertools.combinations(vertices, 2):
        if brancher._get_partition_ids(u) & brancher._get_partition_ids(v):
            continue
        gamma = sum(x for c, x in brancher.solution.items()
                    if brancher._column_contains_vertex(c, u)
                    and brancher._column_contains_vertex(c, v))
        f = abs(gamma-round(gamma))
        if f > best+1e-8:
            best, pair = f, (u.id, v.id)
    return pair


@pytest.mark.parametrize("merged", [False, True])
def test_cached_branch_matches_original_rule(merged):
    inst = instance()
    graph = AuxiliaryGraph(inst.graph, inst.graph.vertex_map)
    if merged:
        graph.same_color(inst.graph.partitions[0].vertex_list[0],
                         inst.graph.partitions[1].vertex_list[1])
    rng = random.Random(19)
    for _ in range(20):
        columns = [col(rng.sample(inst.graph.vertices, rng.randint(1, 6))) for _ in range(12)]
        solution = {c: rng.choice([0.0, 0.25, 0.5, 0.75, 1.0]) for c in columns}
        b = BranchCreator(solution, ColumnPool(), graph)
        expected = reference_pair(b)
        found = b.check_branch_rule2()
        actual = (b.checked_vertex_v.id, b.checked_vertex_u.id) if found else None
        assert actual == expected
