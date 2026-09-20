"""Model equivalence, LP strength and pricing-dual tests on small enumerable instances."""
import itertools
import time

import pytest

gp = pytest.importorskip("gurobipy")
from cg.column_independent_set import ColumnIndependentSet
from cg.column_pool import ColumnPool
from cg.master.master_problem import MasterProblem
from cg.pricing.pricing_problem import PricingProblem
from cg.pricing.exact_pricing_solver import ExactPricingSolver
from cg.pricing.qaia_exact_pricing_solver import QAIAExactPricingSolver
from ev.ev_to_pcp import ev_json_to_instance
from model.a_graph import AuxiliaryGraph


def data_from_windows(windows, chargers):
    return dict(num_vehicles=len(windows), num_chargers=chargers, time_horizon=20,
        vehicles=[dict(id=i, duration=1, candidates=[dict(candidate_id=j, start=s, end=s+1)
            for j, s in enumerate(starts)]) for i, starts in enumerate(windows)])


def complete_master(data):
    inst = ev_json_to_instance(data)
    graph = AuxiliaryGraph(inst.graph, inst.graph.vertex_map)
    pricing = PricingProblem(graph, "test", {})
    pool = ColumnPool()
    edges = {frozenset((e.source.id, e.target.id)) for e in graph.auxiliary_edges}
    for selection in itertools.product(*[[None, *p.vertex_list] for p in inst.graph.partitions]):
        selected = [v for v in selection if v is not None]
        if selected and all(frozenset((a.id, b.id)) not in edges
                            for a, b in itertools.combinations(selected, 2)):
            pool.addColumn(ColumnIndependentSet(selected, pricing, False, "enumeration", 0))
    master = MasterProblem(inst.graph, inst.charger_num, pricing, pool, graph)
    for column in pool.columns:
        master.add_column_to_rmp(column)
    return master, pricing, graph


def test_stronger_lp_and_exact_reduced_costs(monkeypatch):
    data = data_from_windows([[4, 5, 6]], 1)
    values = {}
    for mode in ("vertex", "vehicle"):
        monkeypatch.setenv("BPC_COMPLETION_ROWS", mode)
        master, pricing, graph = complete_master(data)
        solver = ExactPricingSolver(graph, pricing)
        try:
            _, dual, values[mode] = master.solveMaster(time.perf_counter()+5)
            pricing.update_pricing_problem(dual)
            solver._update_dual()
            hybrid = object.__new__(QAIAExactPricingSolver)
            hybrid.auxiliary_graph, hybrid.pricing_problem = graph, pricing
            if mode == "vehicle":
                assert sum(dual["vehicle_makespan"].values()) > 0
            for mapping in master.varMap.values():
                for column, variable in mapping.items():
                    score = solver._calculate_reduced_cost(column)
                    assert score == pytest.approx(-variable.RC)
                    assert hybrid._column_violation(column) == pytest.approx(-variable.RC)
                    assert score == pytest.approx(sum(graph.weight_v[v.id]
                        for v in column.vertex_list) + dual["charger"])
        finally:
            solver.model.dispose()
            master._rmp.dispose()
    assert values["vertex"] == pytest.approx(1 / (1/5 + 1/6 + 1/7))
    assert values["vehicle"] == pytest.approx(5)


@pytest.mark.parametrize("windows,chargers", [([[0, 2], [0, 1]], 1),
    ([[0, 1], [0, 2], [1, 3]], 2), ([[0, 2], [0, 2], [1, 3]], 1)])
def test_integer_optimum_matches_enumerated_schedules(monkeypatch, windows, chargers):
    data = data_from_windows(windows, chargers)
    # Unit-length tasks can be assigned iff simultaneous occupancy <= chargers.
    optimum = min(max(starts)+1 for starts in itertools.product(*windows)
        if max(starts.count(s) for s in set(starts)) <= chargers)
    lp = {}
    for mode in ("vertex", "vehicle"):
        monkeypatch.setenv("BPC_COMPLETION_ROWS", mode)
        master, _, _ = complete_master(data)
        try:
            _, _, lp[mode] = master.solveMaster(time.perf_counter()+5)
            for mapping in master.varMap.values():
                for variable in mapping.values():
                    variable.VType = gp.GRB.BINARY
            master._rmp.optimize()
            assert master._rmp.Status == gp.GRB.OPTIMAL
            assert master._rmp.ObjVal == pytest.approx(optimum)
        finally:
            master._rmp.dispose()
    assert lp["vehicle"] + 1e-7 >= lp["vertex"]


def test_merged_vertices_use_original_times_and_duals(monkeypatch):
    monkeypatch.setenv("BPC_COMPLETION_ROWS", "vehicle")
    inst = ev_json_to_instance(data_from_windows([[0], [2]], 1))
    graph = AuxiliaryGraph(inst.graph, inst.graph.vertex_map)
    a, b = inst.graph.vertices
    graph.same_color(a, b)
    merged = next(iter(graph.merged_vertices_map))
    pricing = PricingProblem(graph, "test", {})
    pool = ColumnPool()
    column = ColumnIndependentSet([merged], pricing, False, "test", 0)
    master = MasterProblem(inst.graph, 1, pricing, pool, graph)
    solver = ExactPricingSolver(graph, pricing)
    try:
        master.add_column_to_rmp(column)
        master._rmp.update()
        variable = master.varMap[pricing][column]
        for v in (a, b):
            row = master.vehicle_makespan_constraints[v.associated_partition.id]
            assert master._rmp.getCoeff(row, variable) == -v.end_time
        dual = dict(partition={0: 10, 1: 20}, makespan={a.id: 0.3, b.id: 0.7}, charger=-2)
        pricing.update_pricing_problem(dual)
        solver._update_dual()
        expected = 10 + 20 - 0.3*1 - 0.7*3 - 2
        assert solver._calculate_reduced_cost(column) == pytest.approx(expected)
        assert graph.weight_v[merged.id] + dual["charger"] == pytest.approx(expected)
        solver.debug = True
        solver._assert_reduced_cost_consistency(expected, column)
    finally:
        master._rmp.dispose()
        solver.model.dispose()
