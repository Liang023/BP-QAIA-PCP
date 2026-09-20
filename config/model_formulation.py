"""Common makespan formulation for BP and the compact MILP benchmark."""
import os


def completion_rows():
    mode = os.getenv("BPC_COMPLETION_ROWS", "vehicle")
    if mode not in {"vertex", "vehicle"}:
        raise ValueError("BPC_COMPLETION_ROWS must be vertex or vehicle")
    return mode
