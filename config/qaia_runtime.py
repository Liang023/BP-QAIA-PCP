"""Single source of truth for Stage 5 runtime settings."""
import math
import os
import json
import hashlib
from pathlib import Path

QAIA_ENV_KEYS = {"QAIA_N_ITER", "QAIA_BATCH_SIZE", "QAIA_DT", "QAIA_XI",
                 "QAIA_MAX_COLUMNS", "QAIA_MAX_STREAK", "QAIA_COLUMN_POLICY",
                 "QAIA_EXACT_MODE", "QAIA_PROVIDER"}


def load_frozen(path):
    raw = Path(path).read_bytes()
    data = json.loads(raw)
    env = data["env"]
    if set(env) - QAIA_ENV_KEYS or env.get("QAIA_PROVIDER") != "qaia":
        raise ValueError("Expected a frozen QAIA configuration")
    return env, dict(path=str(Path(path).resolve()), sha256=hashlib.sha256(raw).hexdigest(),
                    tuning_seconds=data.get("tuning_seconds"),
                    training_protocol=data.get("protocol"),
                    training_instances=data.get("training_instances", []))


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
    if provider not in {"qaia", "greedy", "cim"}:
        raise ValueError("Unknown QAIA_PROVIDER")
    dt = float(os.getenv("QAIA_DT", "1.0"))
    if not math.isfinite(dt) or dt <= 0:
        raise ValueError("QAIA_DT must be positive and finite")
    kwargs = {"dt": dt}
    xi = os.getenv("QAIA_XI", "auto")
    if xi != "auto":
        value = float(xi)
        if not math.isfinite(value) or value <= 0:
            raise ValueError("QAIA_XI must be positive or auto")
        kwargs["xi"] = value
    return dict(
        exact_mode=mode, heuristic_provider=provider,
        max_heuristic_streak=positive_int("QAIA_MAX_STREAK", 3),
        qaia_algorithm="BSB", qaia_backend="cpu-float32",
        qaia_n_iter=positive_int("QAIA_N_ITER", 200),
        qaia_batch_size=positive_int("QAIA_BATCH_SIZE", 10),
        qaia_max_columns=positive_int("QAIA_MAX_COLUMNS", 3),
        qaia_penalty_margin=1.0, normalize_ising=True,
        qaia_algorithm_kwargs=kwargs,
    )
