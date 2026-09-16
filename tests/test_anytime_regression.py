"""Run: python -m pytest -q test/test_anytime_regression.py"""
import json
import math
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from cg.anytime import IncumbentRecorder, recover_history, snapshots


def test_deadline_checked_after_validation(tmp_path):
    clock = [0.1]
    def validator(schedule, value):
        clock[0] = 2.1
    recorder = IncumbentRecorder(0, 2, validator, tmp_path / "trace.jsonl", clock=lambda: clock[0])
    assert not recorder.record([[{}]], 1, "test")
    assert recorder.history == []


def test_trajectory_recovery_and_snapshots(tmp_path):
    clock = [0.2]
    path = tmp_path / "trace.jsonl"
    recorder = IncumbentRecorder(0, 2, path=path, metadata={"instance_sha256": "test"},
                                 clock=lambda: clock[0])
    assert recorder.record([[{"end": 5}]], 5, "test")
    clock[0] = 1.5
    assert recorder.record([[{"end": 3}]], 3, "test")
    assert not recorder.record([[{"end": 4}]], 4, "test")
    with path.open("ab") as f:
        f.write(b'{"event":')
    history = recover_history(path, 2, lambda schedule, value: None, "test")
    assert [e["objective"] for e in history] == [5, 3]
    assert [r["objective"] for r in snapshots(history, [0.1, 1, 2])] == [None, 5, 3]
    with pytest.raises(ValueError, match="instance changed"):
        recover_history(path, 2, lambda schedule, value: None, "wrong")


def test_validation_error_does_not_update_incumbent():
    def invalid(schedule, value):
        raise ValueError("invalid schedule")
    r = IncumbentRecorder(0, 2, validator=invalid, clock=lambda: 1)
    with pytest.raises(ValueError):
        r.record([[{}]], 1, "test")
    assert not r.fields()["has_feasible_solution"]


def test_mid_cg_candidate_precedes_pricing_timeout():
    pytest.importorskip("gurobipy")
    from cg.column_generation import ColumnGeneration
    events = []
    master = SimpleNamespace(solution={"column": 1.0})
    pool = SimpleNamespace(columns=[])
    cg = ColumnGeneration(master, None, None, pool, math.inf, 0,
                          on_candidate=lambda s, o, i: events.append((s, o, i)))
    def solve_master(cols, deadline):
        cg.masterObjective = 7
    def timeout(deadline, dual):
        raise TimeoutError("pricing timeout")
    cg.invokeMaster, cg.invokePricing = solve_master, timeout
    with pytest.raises(TimeoutError):
        cg.solve(time.perf_counter()+2)
    assert events == [({"column": 1.0}, 7, 1)]
    assert cg.solution is None  # incomplete CG has NOT returned a certified node result


def toy_data():
    return dict(num_vehicles=1, num_chargers=1, time_horizon=2,
                vehicles=[dict(id=0, duration=1,
                    candidates=[dict(candidate_id=0, start=0, end=1)])])


def test_bp_retains_rmp_incumbent_when_pricing_times_out(monkeypatch):
    pytest.importorskip("gurobipy")
    from ev.ev_to_pcp import ev_json_to_instance
    from bpc.branch_and_price import BranchAndPrice
    from cg.pricing.exact_pricing_solver import ExactPricingSolver
    inst = ev_json_to_instance(toy_data())
    monkeypatch.setenv("BPC_RMP_MIP", "0")
    bp = BranchAndPrice(inst.graph, inst.charger_num, time_limit=5, use_qaia=False)
    original = bp.update_best_solution
    def ignore_initial(*args, **kwargs):
        if kwargs.get("source") == "initial":
            return False
        return original(*args, **kwargs)
    monkeypatch.setattr(bp, "update_best_solution", ignore_initial)
    def timeout(*args, **kwargs):
        raise TimeoutError("injected pricing timeout")
    monkeypatch.setattr(ExactPricingSolver, "generate_columns", timeout)
    result = bp.solve()
    assert result["status"] == "time_limit"
    assert result["objective_value"] == 1
    assert result["has_feasible_solution"]
    assert result["incumbent_history"][0]["source"] == "rmp_integer"
    assert not result["statistics"]["root_diagnostics"]["cg_certified"]


def test_initialization_timeout_returns_structured_result(monkeypatch):
    pytest.importorskip("gurobipy")
    from ev.ev_to_pcp import ev_json_to_instance
    from bpc.branch_and_price import BranchAndPrice
    inst = ev_json_to_instance(toy_data())
    bp = BranchAndPrice(inst.graph, 1, time_limit=2, use_qaia=False)
    def timeout():
        raise TimeoutError("root construction timeout")
    monkeypatch.setattr(bp, "generate_root_node", timeout)
    result = bp.solve()
    assert result["status"] == "time_limit"
    assert result["objective_value"] is None
    assert result["statistics"]["gap"] is None


def test_graph_deadline_is_not_reset():
    from ev.ev_to_pcp import ev_json_to_instance
    with pytest.raises(TimeoutError):
        ev_json_to_instance(toy_data(), deadline=time.perf_counter()-1)


def test_restricted_mip_does_not_change_lp():
    gp = pytest.importorskip("gurobipy")
    from ev.ev_to_pcp import ev_json_to_instance
    from bpc.branch_and_price import BranchAndPrice
    from cg.master.master_problem import MasterProblem
    from cg.master.restricted_integer_master import solve_restricted_mip
    from cg.pricing.pricing_problem import PricingProblem
    inst = ev_json_to_instance(toy_data())
    bp = BranchAndPrice(inst.graph, 1, 5, use_qaia=False)
    root = bp.generate_root_node()
    pricing = PricingProblem(root.a_graph, "test", {})
    master = MasterProblem(inst.graph, 1, pricing, root.column_pool, root.a_graph)
    try:
        for col in root.column_pool.columns:
            master.add_column_to_rmp(col)
        master._rmp.update()
        before = [(v.VType, v.UB) for v in master._rmp.getVars()]
        found = []
        solve_restricted_mip(master, time.perf_counter()+2, 1,
                            lambda solution, objective: found.append((solution, objective)))
        assert found
        assert all(not c.is_artificial_column for sol, _ in found for c in sol)
        assert [(v.VType, v.UB) for v in master._rmp.getVars()] == before
        assert all(v.VType == gp.GRB.CONTINUOUS for v in master._rmp.getVars())
    finally:
        master._rmp.dispose()


def test_nonfinite_or_fractional_values_are_not_integer():
    pytest.importorskip("gurobipy")
    from bpc.branch_and_price import BranchAndPrice
    obj = object.__new__(BranchAndPrice)
    for value in (float("nan"), float("inf"), 0.4, object()):
        assert not obj.is_integer_solution({"x": value})


def test_physical_objective_and_canonical_columns_agree():
    pytest.importorskip("gurobipy")
    from ev.ev_to_pcp import ev_json_to_instance
    from bpc.branch_and_price import BranchAndPrice
    from cg.column_independent_set import ColumnIndependentSet
    from validation.ev_solution import validate_schedule
    data = toy_data()
    data["time_horizon"] = 5
    data["num_chargers"] = 2
    data["vehicles"][0]["candidates"].append(dict(candidate_id=1, start=4, end=5))
    inst = ev_json_to_instance(data)
    bp = BranchAndPrice(inst.graph, 2, 5, use_qaia=False)
    root = bp.generate_root_node()
    start = time.perf_counter()
    bp.recorder = IncumbentRecorder(start, start+5)
    bp.deadline = start+5
    bp.best_objective = 3  # incoming column-model objective 5 is worse, physical objective 1 is better
    solution = {ColumnIndependentSet([v], "test", False, "test", 0): 1.0
                for v in inst.graph.vertices}
    assert bp.update_best_solution(5, solution, a_graph=root.a_graph)
    assert bp.best_objective == 1
    assert len(bp.best_solution) == 1
    assert validate_schedule(bp.best_solution, root.a_graph, inst.graph, 2, 1)["makespan"] == 1
