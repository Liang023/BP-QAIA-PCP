import math
import time


def remaining_seconds(time_end: float, stage: str) -> float:
    """time_end must use the same perf_counter clock as BranchAndPrice.solve."""
    remaining = float(time_end) - time.perf_counter()
    if not math.isfinite(remaining):
        raise ValueError(f"{stage}: invalid deadline")
    if remaining <= 0:
        raise TimeoutError(f"{stage}: global time budget exhausted")
    return remaining