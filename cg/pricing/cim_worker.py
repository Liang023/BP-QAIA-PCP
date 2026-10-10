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
    context = request.get("replay_context") or {}
    record_encoding = bool(context)
    sample_limit = int(context["sample_limit"]) if context.get("sample_limit") is not None else None
    if sample_limit is not None and sample_limit <= 0:
        raise ValueError("Replay sample limit must be positive")
    build_started = time.perf_counter()
    matrix, variables = prepare_model(request, kw)
    ids, options = request["ids"], request["options"]
    submitted = matrix.copy()
    submitted[np.abs(submitted) < 1e-10] = 0
    if record_encoding:
        np.save(directory / "sdk_ising_matrix.npy", matrix)
        np.save(directory / "pre_quantization_matrix.npy", submitted)
    encoding = dict(kaiwu_version=getattr(kw, "__version__", "unknown"),
        sdk_matrix_shape=list(matrix.shape), variable_order=[str(v) for v in variables],
        precision=options["precision"], target_bits=options["max_bits"],
        zero_threshold=1e-10, applied=True, actual_device_input_saved=False,
        encoding_seconds=time.perf_counter()-build_started,
        submission_attempts=0,
        submission_count_basis="SDK create-task calls; acceptance and completion may be unknown after timeout",
        classical_comparison="SDK uses augmented Ising/gauge encoding; compare saved conventions and matrices",
        strict_no_retry=bool(context.get("strict_no_retry")))
    def save_encoding():
        if record_encoding:
            (directory / "encoding_metadata.json").write_text(json.dumps(encoding, indent=2), encoding="utf-8")
    save_encoding()
    kw.common.CheckpointManager.save_dir = str(directory)
    base = kw.cim.CIMOptimizer(task_name=request["task"], interval=1, wait=True,
        access_key=os.environ["ECLOUD_ACCESS_KEY"], secret_key=os.environ["ECLOUD_SECRET_KEY"],
        device_id=options["device_id"])
    component = base
    if encoding["strict_no_retry"]:
        # The eCloud SDK's HTTP retry setting is explicit and persisted. Fail
        # before a request if an incompatible SDK cannot enforce this policy.
        retry_config = base._runner.wuyue_client.config
        retry_config.auto_retry = False
        retry_config.max_retry_times = 0
        original_create = base._create_task
        submissions = [0]
        def create_once(*args, **kwargs):
            submissions[0] += 1
            if submissions[0] > 1:
                raise RuntimeError("Additional CIM submission blocked: retries disabled")
            encoding["submission_attempts"] = submissions[0]
            save_encoding()
            return original_create(*args, **kwargs)
        base._create_task = create_once
        class CaptureInput(kw.core.OptimizerBase):
            def __init__(self):
                super().__init__()
                self.calls = 0
            def solve(self, matrix):
                self.calls += 1
                if self.calls > 1:
                    raise RuntimeError("Precision reducer additional solve blocked: one new request per run")
                self.set_matrix(matrix)
                device_matrix = np.asarray(matrix).copy()
                np.save(directory / "device_input_matrix.npy", device_matrix)
                encoding.update(actual_device_input_saved=True,
                    device_matrix_shape=list(device_matrix.shape),
                    device_matrix_dtype=str(device_matrix.dtype),
                    retry_policy=dict(auto_retry=False, max_retry_times=0, max_submissions=1))
                if device_matrix.shape == submitted.shape:
                    denominator = float(np.sum(submitted * submitted))
                    scale = float(np.sum(device_matrix * submitted) / denominator) if denominator else 1.0
                    encoding.update(device_to_sdk_fit_scale=scale,
                        max_abs_quantization_residual=float(np.max(np.abs(device_matrix-scale*submitted))),
                        comparison_scope="actual device vs pre-quantization SDK matrix after fitted scaling")
                else:
                    encoding["comparison_scope"] = "precision reduction changed dimension; inspect both saved matrices"
                save_encoding()
                cloud_started = time.perf_counter()
                try:
                    device_output = base.solve(matrix)
                    if device_output is None:
                        return None
                    device_output = np.atleast_2d(np.asarray(device_output))
                    np.save(directory / "device_output_spins.npy", device_output)
                    encoding["raw_device_received_sample_count"] = int(device_output.shape[0])
                    encoding["device_sample_cap_policy"] = "first device outputs before PrecisionReducer postprocessing and energy sorting"
                    return device_output[:sample_limit] if sample_limit is not None else device_output
                finally:
                    encoding["device_call_seconds"] = time.perf_counter()-cloud_started
                    encoding["submission_attempts"] = submissions[0]
                    save_encoding()
        component = CaptureInput()
    optimizer = kw.cim.PrecisionReducer(component, options["precision"],
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
    if record_encoding:
        np.save(directory / "raw_spins.npy", spins)
    encoding["raw_decoded_sample_count"] = int(spins.shape[0])
    encoding["raw_received_sample_count"] = encoding.get("raw_device_received_sample_count", int(spins.shape[0]))
    if spins.size == 0 or not np.isfinite(spins).all():
        raise ValueError("CIM returned empty or nonfinite samples")
    if np.isin(spins, [0, 1]).all():
        spins = 2*spins-1
    if not np.isin(spins, [-1, 1]).all():
        raise ValueError("Expected CIM spins in {-1,+1}")
    if sample_limit is not None:
        # Enforce the common budget before selecting/sorting by any energy.
        spins = spins[:sample_limit]
        encoding["sample_cap_policy"] = "first physical output samples, before energy sorting"
        encoding["evaluated_sample_count"] = int(spins.shape[0])
    energies = np.asarray(kw.common.hamiltonian(matrix, spins)).reshape(-1)
    order = np.argsort(energies)
    decoded = [kw.core.get_sol_dict(spins[i], variables) for i in order]
    encoding["decoded_sample_order"] = order.tolist()
    save_encoding()
    # Algebraically absent zero-coefficient variables may be omitted by Kaiwu.
    samples = np.array([[row.get(f"x_{v}", 0) for row in decoded] for v in ids])
    if not np.isin(samples, [0, 1]).all():
        raise ValueError("Kaiwu variable decoding must return binary values")
    (directory/"sdk_metadata.json").write_text(json.dumps(dict(
        kaiwu_version=getattr(kw, "__version__", "unknown"), matrix_shape=list(matrix.shape),
        returned_samples=len(decoded), received_samples=encoding["raw_received_sample_count"],
        original_energy_min=float(energies.min()))), encoding="utf-8")
    return samples.astype(np.int8)


def main():
    import kaiwu as kw
    request_path, result_path = map(Path, sys.argv[1:])
    request = json.loads(request_path.read_text(encoding="utf-8"))
    np.save(result_path, solve_request(request, request_path.parent, kw))


if __name__ == "__main__":
    main()
