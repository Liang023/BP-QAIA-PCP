import math
from cg import budget_clock


def remaining_seconds(time_end: float, stage: str) -> float:
    """time_end must use the same budget_clock clock as BranchAndPrice.solve."""
    remaining = float(time_end) - budget_clock.now()
    if not math.isfinite(remaining):
        raise ValueError(f"{stage}: invalid deadline")
    if remaining <= 0:
        raise TimeoutError(f"{stage}: global time budget exhausted")
    return remaining