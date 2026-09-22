import pytest

pytest.importorskip("gurobipy")
from bpc.branch_and_price import BranchAndPrice
from ev.ev_to_pcp import ev_json_to_instance


@pytest.mark.parametrize("enabled", ["0", "1"])
def test_exact_completion_keeps_optimum(monkeypatch, enabled):
    monkeypatch.setenv("BPC_PRIMAL_COMPLETION", enabled)
    monkeypatch.setenv("EXACT_POOL_SEARCH_MODE", "0")
    data = dict(num_vehicles=3, num_chargers=2, time_horizon=10,
        vehicles=[dict(id=i, duration=1, candidates=[
            dict(candidate_id=j, start=j, end=j+1) for j in range(3)]) for i in range(3)])
    inst = ev_json_to_instance(data)
    bp = BranchAndPrice(inst.graph, 2, 5, use_qaia=False)
    result = bp.solve()
    assert result["status"] == "optimal", result.get("error")
    assert result["objective_value"] == 2
    assert result["statistics"]["primal_completion"]["calls"] == int(enabled)
