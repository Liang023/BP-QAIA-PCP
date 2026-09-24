"""Shared configuration and experiment metadata for primal heuristics."""
import math
import os


PRIMAL_DEFAULTS = {
    "BPC_PRIMAL_COMPLETION": "0", "BPC_PRIMAL_ATTEMPTS": "20",
    "BPC_PRIMAL_SECONDS": "2", "BPC_PRIMAL_INJECTION": "best",
    "BPC_NEIGHBORHOOD": "0", "BPC_NEIGHBORHOOD_SECONDS": "2",
    "BPC_NEIGHBORHOOD_INTERVAL": "30", "BPC_NEIGHBORHOOD_COOLDOWN": "10",
    "BPC_NEIGHBORHOOD_FRACTION": "0.05", "BPC_NEIGHBORHOOD_VEHICLES": "4",
}


def primal_environment():
    return {key: os.getenv(key, default) for key, default in PRIMAL_DEFAULTS.items()}


def primal_options():
    env = primal_environment()
    root = dict(enabled=env["BPC_PRIMAL_COMPLETION"] == "1",
                attempts=int(env["BPC_PRIMAL_ATTEMPTS"]),
                seconds=float(env["BPC_PRIMAL_SECONDS"]),
                injection=env["BPC_PRIMAL_INJECTION"])
    neighborhood = dict(enabled=env["BPC_NEIGHBORHOOD"] == "1",
        seconds=float(env["BPC_NEIGHBORHOOD_SECONDS"]),
        interval=float(env["BPC_NEIGHBORHOOD_INTERVAL"]),
        cooldown=float(env["BPC_NEIGHBORHOOD_COOLDOWN"]),
        fraction=float(env["BPC_NEIGHBORHOOD_FRACTION"]),
        vehicles=int(env["BPC_NEIGHBORHOOD_VEHICLES"]))
    if (root["attempts"] < 1 or root["injection"] not in {"best", "all"}
            or neighborhood["vehicles"] < 1
            or not 0 <= neighborhood["fraction"] <= 1
            or any(not math.isfinite(v) or v <= 0 for v in (
                root["seconds"], neighborhood["seconds"], neighborhood["interval"],
                neighborhood["cooldown"]))):
        raise ValueError("Invalid primal heuristic settings")
    return root, neighborhood
