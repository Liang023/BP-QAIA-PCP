"""BP clock: exclude measured blocking cloud calls, retain local computation."""
import time

_excluded = 0.0


def reset():
    global _excluded
    _excluded = 0.0


def now():
    return time.perf_counter() - _excluded


def exclude_cloud_seconds(seconds):
    global _excluded
    _excluded += seconds


def excluded_seconds():
    return _excluded
