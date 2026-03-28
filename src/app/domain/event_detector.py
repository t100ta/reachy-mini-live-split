from __future__ import annotations

from app.clock import now as _now
from app.config import AppConfig
from app.domain.events import (
    PACE_AHEAD,
    PACE_BEHIND,
    PACE_NEUTRAL,
    RUN_FINISHED,
    RUN_RESET,
    RUN_STARTED,
    SPLIT_BAD,
    SPLIT_CHANGED,
    SPLIT_GOOD,
    SPLIT_UNDO,
    InternalEvent,
)
from app.domain.thresholds import classify_pace
from app.livesplit.snapshot import LiveSplitSnapshot

_RUNNING_PHASES = {"Running", "Paused"}
_NOT_RUNNING = "NotRunning"
_ENDED = "Ended"


def detect_events(
    prev: LiveSplitSnapshot | None,
    curr: LiveSplitSnapshot,
    cfg: AppConfig,
) -> list[InternalEvent]:
    """
    前回スナップショットと今回スナップショットを比較し、
    発生したイベントのリストを返す。
    """
    t = _now()
    events: list[InternalEvent] = []

    if prev is None:
        # 初回ポーリング: 現在の状態からイベントを起こさない
        return events

    prev_running = prev.timer_phase in _RUNNING_PHASES
    curr_running = curr.timer_phase in _RUNNING_PHASES

    # run_started: NotRunning → Running
    if not prev_running and curr.timer_phase == "Running":
        events.append(InternalEvent(RUN_STARTED, t, {"attempt": curr.attempt_count}))

    # run_reset: Running/Paused → NotRunning
    elif prev_running and curr.timer_phase == _NOT_RUNNING:
        events.append(InternalEvent(RUN_RESET, t))

    # run_finished: → Ended
    if curr.timer_phase == _ENDED and prev.timer_phase != _ENDED:
        events.append(
            InternalEvent(
                RUN_FINISHED,
                t,
                {
                    "time": curr.current_time,
                    "attempt": curr.attempt_count,
                },
            )
        )

    # split_changed: split_index 増加
    if (
        curr_running
        and prev.split_index >= 0
        and curr.split_index > prev.split_index
    ):
        payload: dict = {
            "split_index": curr.split_index,
            "split_name": curr.current_split_name,
            "delta": curr.delta,
        }
        events.append(InternalEvent(SPLIT_CHANGED, t, payload))

        # split_good / split_bad: delta の変化から判定
        if prev.delta is not None and curr.delta is not None:
            if curr.delta < prev.delta:
                events.append(InternalEvent(SPLIT_GOOD, t, payload))
            elif curr.delta > prev.delta:
                events.append(InternalEvent(SPLIT_BAD, t, payload))
            # delta が変わらない（完全に同じ）場合は good 扱い
            else:
                events.append(InternalEvent(SPLIT_GOOD, t, payload))
        elif curr.delta is not None and curr.delta < 0:
            events.append(InternalEvent(SPLIT_GOOD, t, payload))
        else:
            # delta データなし（PB未設定等）: good として扱う
            events.append(InternalEvent(SPLIT_GOOD, t, payload))

    # split_undo: split_index 減少（undo split）
    elif (
        curr_running
        and prev.split_index > 0
        and curr.split_index < prev.split_index
    ):
        payload = {
            "split_index": curr.split_index,
            "split_name": curr.current_split_name,
        }
        events.append(InternalEvent(SPLIT_UNDO, t, payload))

    # pace: 現在の pace bucket を毎回通知
    if curr_running and curr.timer_phase == "Running":
        pace = classify_pace(curr.delta, cfg.thresholds)
        pace_event_name = {
            "ahead": PACE_AHEAD,
            "neutral": PACE_NEUTRAL,
            "behind": PACE_BEHIND,
        }[pace.value]
        events.append(InternalEvent(pace_event_name, t, {"delta": curr.delta}))

    return events
