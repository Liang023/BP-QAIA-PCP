"""One cloud request, using the API demonstrated in the uploaded QBendersOCT.py."""
import json
import inspect
import os
from pathlib import Path
import sys
import time

import numpy as np


def check_interface(kw):
    parameters = inspect.signature(kw.cim.CIMOptimizer).parameters
    required = {"access_key", "secret_key", "device_id", "task_name", "wait"}
    if not required <= set(parameters) and not any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in parameters.values()):
        raise RuntimeError("This adapter requires the eCloud CIMOptimizer API from QBendersOCT.py; "
                           "the installed Kaiwu SDK exposes a different constructor")


def prepare_model(request, kw):
    ids, weights = request["ids"], request["weights"]
    x = {v: kw.core.Binary(f"x_{v}") for v in ids}
    penalty = request["penalty"]
    model = kw.qubo.QuboModel()
    objective = -sum(w*x[v] for v, w in zip(ids, weights))
    objective += penalty*sum(x[u]*x[v] for u, v in request["edges"])
    objective += penalty*sum(x[v] for v in request["forbidden"])
    model.set_objective(objective)
    ising = kw.conversion.qubo_model_to_ising_model(model)
    matrix = np.asarray(ising.get_matrix(), dtype=float)
    variables = ising.get_variables()
    options = request["options"]
    if matrix.shape[0] > options["max_bits"]:
        raise ValueError("Converted CIM matrix exceeds the device size limit")
    return matrix, variables


def solve_request(request, directory, kw):
    check_interface(kw)
    matrix, variables = prepare_model(request, kw)
    ids, options = request["ids"], request["options"]
    submitted = matrix.copy()
    submitted[np.abs(submitted) < 1e-10] = 0
    kw.common.CheckpointManager.save_dir = str(directory)
    base = kw.cim.CIMOptimizer(task_name=request["task"], interval=1, wait=True,
        access_key=os.environ["ECLOUD_ACCESS_KEY"], secret_key=os.environ["ECLOUD_SECRET_KEY"],
        device_id=options["device_id"])
    optimizer = kw.cim.PrecisionReducer(base, options["precision"],
                                       target_bits=options["max_bits"])
    # Measure precisely the blocking SDK call. Model construction and decoding
    # remain part of the BP budget. The SDK handles its own task cache.
    started = time.perf_counter()
    try:
        raw = optimizer.solve(submitted)
    finally:
        (directory / "cloud_timing.json").write_text(json.dumps(dict(
            cloud_call_seconds=time.perf_counter() - started,
            scope="optimizer.solve: upload, queue, cloud compute and response")),
            encoding="utf-8")
    if raw is None:
        raise RuntimeError("CIM returned no samples")
    spins = np.atleast_2d(np.asarray(raw))
    if spins.size == 0 or not np.isfinite(spins).all():
        raise ValueError("CIM returned empty or nonfinite samples")
    if np.isin(spins, [0, 1]).all():
        spins = 2*spins-1
    if not np.isin(spins, [-1, 1]).all():
        raise ValueError("Expected CIM spins in {-1,+1}")
    energies = np.asarray(kw.common.hamiltonian(matrix, spins)).reshape(-1)
    decoded = [kw.core.get_sol_dict(spins[i], variables) for i in np.argsort(energies)]
    # Algebraically absent zero-coefficient variables may be omitted by Kaiwu.
    samples = np.array([[row.get(f"x_{v}", 0) for row in decoded] for v in ids])
    if not np.isin(samples, [0, 1]).all():
        raise ValueError("Kaiwu variable decoding must return binary values")
    (directory/"sdk_metadata.json").write_text(json.dumps(dict(
        kaiwu_version=getattr(kw, "__version__", "unknown"), matrix_shape=list(matrix.shape),
        returned_samples=len(decoded), original_energy_min=float(energies.min()))), encoding="utf-8")
    return samples.astype(np.int8)


def main():
    import kaiwu as kw
    request_path, result_path = map(Path, sys.argv[1:])
    request = json.loads(request_path.read_text(encoding="utf-8"))
    np.save(result_path, solve_request(request, request_path.parent, kw))


if __name__ == "__main__":
    main()
