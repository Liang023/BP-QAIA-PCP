"""Deadline-aware incumbent records; no solver dependencies."""
import copy
import json
import math
import time
from pathlib import Path


class IncumbentRecorder:
    def __init__(self, start_time, deadline, validator=None, path=None, metadata=None,
                 clock=time.perf_counter):
        if not (math.isfinite(start_time) and math.isfinite(deadline)
                and deadline > start_time):
            raise ValueError("invalid global time budget")
        self.start_time, self.deadline = start_time, deadline
        self.validator, self.clock = validator, clock
        self.history = []
        self.path = Path(path) if path else None
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("x", encoding="utf-8") as f:
                f.write(json.dumps(dict(event="metadata", budget=deadline-start_time,
                                        **(metadata or {})), ensure_ascii=False,
                                   allow_nan=False) + "\n")

    def record(self, schedule, objective, source, node_id=None, cg_iteration=None):
        if self.clock() > self.deadline:
            return False
        if not math.isfinite(float(objective)) or not schedule:
            raise ValueError("incumbent must have a finite objective and schedule")
        # Validate before changing any incumbent state; includes original JSON checks.
        if self.validator:
            self.validator(schedule, objective)
        if self.history and objective >= self.history[-1]["objective"] - 1e-6:
            return False
        payload = copy.deepcopy(schedule)
        now = self.clock()
        if now > self.deadline:
            return False
        event = dict(event="incumbent", elapsed_seconds=max(0.0, now-self.start_time),
                     objective=float(objective), source=source, node_id=node_id,
                     cg_iteration=cg_iteration, validation_passed=True, schedule=payload)
        # Flush each complete event; a killed process can leave a partial final line.
        if self.path:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
                f.flush()
        self.history.append(event)
        return True

    def fields(self):
        last = self.history[-1] if self.history else None
        return dict(has_feasible_solution=bool(last),
                    best_objective=last["objective"] if last else None,
                    time_to_first_feasible=self.history[0]["elapsed_seconds"] if last else None,
                    best_found_seconds=last["elapsed_seconds"] if last else None,
                    incumbent_history=copy.deepcopy(self.history),
                    trajectory_file=str(self.path) if self.path else None)


def snapshots(history, checkpoints):
    """Right-continuous step function; never interpolate or fill an absent solution."""
    return [{"seconds": float(t), "objective": next(
        (e["objective"] for e in reversed(history) if e["elapsed_seconds"] <= t), None)}
        for t in checkpoints]


def recover_history(path, budget, validator, expected_sha=None):
    """Recover complete, validated in-budget records after an external timeout."""
    p = Path(path)
    if not p.exists():
        return []
    lines = p.read_bytes().splitlines(keepends=True)
    history = []
    for index, line in enumerate(lines):
        try:
            event = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            if index == len(lines)-1 and not line.endswith(b"\n"):
                break
            raise ValueError("invalid trajectory record")
        if index == 0:
            if event.get("event") != "metadata":
                raise ValueError("trajectory header missing")
            if expected_sha and event.get("instance_sha256") != expected_sha:
                raise ValueError("trajectory instance changed")
            if abs(float(event["budget"])-budget) > 1e-5:
                raise ValueError("trajectory budget changed")
            continue
        t, objective = event["elapsed_seconds"], event["objective"]
        if not (math.isfinite(t) and math.isfinite(objective) and 0 <= t <= budget):
            raise ValueError("invalid incumbent timestamp or objective")
        if history and (t < history[-1]["elapsed_seconds"] or
                        objective >= history[-1]["objective"]-1e-6):
            raise ValueError("nonmonotone incumbent history")
        validator(event["schedule"], objective)
        history.append(event)
    return history
