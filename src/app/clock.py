import time


def now() -> float:
    """Return current monotonic time in seconds."""
    return time.monotonic()


def wall_now() -> float:
    """Return current wall-clock time (Unix timestamp)."""
    return time.time()
