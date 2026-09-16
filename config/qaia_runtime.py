"""Single source of truth for Stage 5 runtime settings."""
import math
import os


def positive_int(name, default):
    value = int(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def pricing_options():
    mode = os.getenv("QAIA_EXACT_MODE", "always")
    provider = os.getenv("QAIA_PROVIDER", "qaia")
    if mode not in {"always", "on_qaia_failure"}:
        raise ValueError("Unknown QAIA_EXACT_MODE")
    if provider not in {"qaia", "greedy"}:
        raise ValueError("Unknown QAIA_PROVIDER")
    dt = float(os.getenv("QAIA_DT", "1.0"))
    if not math.isfinite(dt) or dt <= 0:
        raise ValueError("QAIA_DT must be positive and finite")
    return dict(
        exact_mode=mode, heuristic_provider=provider,
        max_heuristic_streak=positive_int("QAIA_MAX_STREAK", 3),
        qaia_algorithm="BSB", qaia_backend="cpu-float32",
        qaia_n_iter=positive_int("QAIA_N_ITER", 200),
        qaia_batch_size=positive_int("QAIA_BATCH_SIZE", 10),
        qaia_max_columns=positive_int("QAIA_MAX_COLUMNS", 3),
        qaia_penalty_margin=1.0, normalize_ising=True,
        qaia_algorithm_kwargs={"dt": dt},
    )