import json
import subprocess
import time
from types import SimpleNamespace

import numpy as np
import pytest

from config.qaia_runtime import load_frozen, pricing_options
from experiments.tune_qaia import quality_score
from cg.pricing.cim_backend import CIMBackend
from cg.pricing.cim_worker import check_interface, solve_request
from cg import budget_clock


def test_frozen_xi_reaches_solver_options(tmp_path, monkeypatch):
    path = tmp_path/"frozen.json"
    path.write_text(json.dumps(dict(env={"QAIA_PROVIDER": "qaia", "QAIA_XI": "0.7"},
                                    tuning_seconds=123)), encoding="utf-8")
    env, meta = load_frozen(path)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    assert pricing_options()["qaia_algorithm_kwargs"]["xi"] == 0.7
    assert meta["tuning_seconds"] == 123 and len(meta["sha256"]) == 64


def test_tuning_loss_prioritizes_feasibility_without_fake_objective():
    feasible = dict(validation_passed=True, has_feasible_solution=True, objective=10)
    missing = dict(validation_passed=False, has_feasible_solution=False, objective=None)
    assert quality_score([feasible, feasible], [10, 10]) < quality_score([feasible, missing], [10, 10])
    assert missing["objective"] is None


def test_cim_unlimited_wait_size_and_call_cap(tmp_path, monkeypatch):
    monkeypatch.setenv("CIM_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("ECLOUD_ACCESS_KEY", "test-key")
    monkeypatch.setenv("ECLOUD_SECRET_KEY", "test-secret")
    backend = CIMBackend()
    backend.options["max_calls"] = 1
    def worker(command, **kwargs):
        assert "timeout" not in kwargs
        from pathlib import Path
        np.save(command[-1], np.array([[1]], dtype=np.int8))
        (Path(command[-1]).parent / "cloud_timing.json").write_text(
            json.dumps(dict(cloud_call_seconds=0)))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(subprocess, "run", worker)
    sample = backend.sample([0], {0: 2}, {0: set()}, set(), 1, budget_clock.now()+5)
    assert sample.shape == (1, 1)
    assert backend.metrics["timeouts"] == 0 and backend.metrics["completed"] == 1
    backend.sample([0], {0: 2}, {0: set()}, set(), 1, time.perf_counter()+5)
    assert backend.metrics["requests"] == 1
    # No credentials in the on-disk request.
    assert "test-secret" not in next(tmp_path.rglob("request.json")).read_text()
    backend.options["max_bits"] = 2
    backend.sample([0, 1], {}, {}, set(), 1, time.perf_counter()+5)
    assert backend.metrics["size_skips"] == 1


def test_cim_success_decoding_and_repair(monkeypatch, tmp_path):
    monkeypatch.setenv("CIM_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("ECLOUD_ACCESS_KEY", "test-key")
    monkeypatch.setenv("ECLOUD_SECRET_KEY", "test-secret")
    def fake_worker(command, **kwargs):
        from pathlib import Path
        np.save(command[-1], np.array([[1, 0], [1, 1]], dtype=np.int8))
        (Path(command[-1]).parent / "cloud_timing.json").write_text(
            json.dumps(dict(cloud_call_seconds=0)))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(subprocess, "run", fake_worker)
    backend = CIMBackend()
    samples = backend.sample([0, 1], {0: 2, 1: 1}, {0: {1}, 1: {0}}, set(), 1,
                             time.perf_counter()+5)
    from cg.pricing.qaia_exact_pricing_solver import QAIAPricingSolver
    assert backend.metrics["completed"] == 1
    assert QAIAPricingSolver._repair_independent_set(set(np.flatnonzero(samples[:, 0])),
        [0, 1], {0: 2, 1: 1}, {0: {1}, 1: {0}}, set()) == {0}


def test_incompatible_public_sdk_is_reported():
    kw = SimpleNamespace(cim=SimpleNamespace(CIMOptimizer=lambda task_name: None))
    with pytest.raises(RuntimeError, match="eCloud"):
        check_interface(kw)


def test_worker_qubo_and_original_energy_order(tmp_path, monkeypatch):
    # Mock SDK boundary only: exhaustively evaluate the actual constructed QUBO.
    class Expr:
        def __init__(self, fn): self.fn = fn
        def __add__(self, other):
            return Expr(lambda x: self.fn(x)+(other.fn(x) if isinstance(other, Expr) else other))
        __radd__ = __add__
        def __mul__(self, other):
            return Expr(lambda x: self.fn(x)*(other.fn(x) if isinstance(other, Expr) else other))
        __rmul__ = __mul__
        def __neg__(self): return self * -1
    class Model:
        def set_objective(self, value): self.value = value
    def convert(model):
        assert [model.value.fn(x) for x in [(0,0), (1,0), (0,1), (1,1)]] == [0,-2,-1,0]
        return SimpleNamespace(get_matrix=lambda: np.zeros((2,2)), get_variables=lambda: ["x_0", "x_1"])
    received = {}
    def optimizer(**kwargs):
        received.update(kwargs)
        return object()
    def reducer(base, precision, target_bits):
        assert precision == 8 and target_bits == 1000
        return SimpleNamespace(solve=lambda matrix: np.array([[-1,1],[1,-1]]))
    kw = SimpleNamespace(core=SimpleNamespace(Binary=lambda name: Expr(lambda x: x[int(name[2:])]),
        get_sol_dict=lambda s, names: dict(zip(names, (s+1)//2))),
        qubo=SimpleNamespace(QuboModel=Model), conversion=SimpleNamespace(qubo_model_to_ising_model=convert),
        cim=SimpleNamespace(CIMOptimizer=optimizer, PrecisionReducer=reducer),
        common=SimpleNamespace(CheckpointManager=SimpleNamespace(), hamiltonian=lambda m,s: [-1,-2]))
    monkeypatch.setenv("ECLOUD_ACCESS_KEY", "fake")
    monkeypatch.setenv("ECLOUD_SECRET_KEY", "fake")
    request = dict(ids=[0,1], weights=[2,1], edges=[[0,1]], forbidden=[], penalty=3,
        task="test", options=dict(max_bits=1000, precision=8, device_id="mock"))
    samples = solve_request(request, tmp_path, kw)
    assert samples.tolist() == [[1,0],[0,1]]
    assert received["wait"] is True and received["device_id"] == "mock"
