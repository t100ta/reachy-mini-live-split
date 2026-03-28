from enum import Enum


class HighLevelState(str, Enum):
    IDLE = "idle"
    READY = "ready"
    RUNNING_NEUTRAL = "running_neutral"
    RUNNING_AHEAD = "running_ahead"
    RUNNING_BEHIND = "running_behind"
    PAUSED = "paused"
    FINISHED = "finished"
    DISCONNECTED = "disconnected"
    SAFE_MODE = "safe_mode"


class PaceBucket(str, Enum):
    AHEAD = "ahead"
    NEUTRAL = "neutral"
    BEHIND = "behind"
