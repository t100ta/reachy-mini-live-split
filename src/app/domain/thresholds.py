from __future__ import annotations

from app.config import ThresholdsConfig
from app.types import PaceBucket


def classify_pace(delta: float | None, cfg: ThresholdsConfig) -> PaceBucket:
    """
    delta（秒）を PaceBucket に分類する。
    delta が None（データなし）の場合は NEUTRAL を返す。
    """
    if delta is None:
        return PaceBucket.NEUTRAL
    if delta <= cfg.ahead_seconds:
        return PaceBucket.AHEAD
    if delta >= cfg.behind_seconds:
        return PaceBucket.BEHIND
    return PaceBucket.NEUTRAL
