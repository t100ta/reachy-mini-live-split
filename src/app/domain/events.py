from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# イベント名定数
RUN_STARTED = "run_started"
RUN_RESET = "run_reset"
RUN_FINISHED = "run_finished"
SPLIT_CHANGED = "split_changed"
SPLIT_GOOD = "split_good"
SPLIT_BAD = "split_bad"
SPLIT_UNDO = "split_undo"
PACE_AHEAD = "pace_ahead"
PACE_BEHIND = "pace_behind"
PACE_NEUTRAL = "pace_neutral"


@dataclass(frozen=True)
class InternalEvent:
    """アプリ内部で発火するイベント。"""

    name: str
    """イベント名（上記定数を使用）。"""

    at: float
    """発生時刻（monotonic 秒）。"""

    payload: dict[str, Any] = field(default_factory=dict)
    """追加情報（split名, delta値 等）。"""
