from __future__ import annotations

from dataclasses import dataclass

from app.clock import now as _now
from app.config import AppConfig
from app.domain.events import (
    PACE_AHEAD,
    PACE_BEHIND,
    PACE_NEUTRAL,
    RUN_FINISHED,
    RUN_RESET,
    RUN_STARTED,
    InternalEvent,
)
from app.domain.thresholds import classify_pace
from app.livesplit.snapshot import LiveSplitSnapshot
from app.types import HighLevelState, PaceBucket


@dataclass
class RuntimeState:
    """アプリの実行時状態。"""

    state: HighLevelState = HighLevelState.IDLE
    pace: PaceBucket = PaceBucket.NEUTRAL
    last_motion: str | None = None
    last_snapshot: LiveSplitSnapshot | None = None
    state_entered_at: float = 0.0
    impulse_until: float = 0.0
    """スプリット優先ウィンドウの終了時刻（monotonic 秒）。"""
    pace_changed_at: float = 0.0
    """pace bucket が変化した時刻（デバウンス用）。"""
    pending_pace: PaceBucket | None = None
    """デバウンス中の pace bucket。"""


def transition(
    state: RuntimeState,
    events: list[InternalEvent],
    snapshot: LiveSplitSnapshot | None,
    cfg: AppConfig,
    t: float | None = None,
) -> RuntimeState:
    """
    イベントとスナップショットをもとに RuntimeState を更新して返す。
    state は in-place で更新する（同一オブジェクトを返す）。
    """
    if t is None:
        t = _now()

    th = cfg.thresholds
    debounce_s = th.pace_debounce_ms / 1000.0
    ready_s = th.ready_duration_ms / 1000.0
    split_priority_s = th.split_priority_ms / 1000.0

    event_names = {e.name for e in events}

    # --- 接続断から復帰 ---
    if snapshot is not None and state.state == HighLevelState.DISCONNECTED:
        _enter(state, HighLevelState.IDLE, t)

    # --- 致命的イベント（優先度高） ---
    if RUN_FINISHED in event_names:
        _enter(state, HighLevelState.FINISHED, t)
        state.last_snapshot = snapshot
        return state

    if RUN_RESET in event_names:
        _enter(state, HighLevelState.IDLE, t)
        state.last_snapshot = snapshot
        return state

    if RUN_STARTED in event_names:
        _enter(state, HighLevelState.READY, t)
        state.impulse_until = t + split_priority_s
        state.last_snapshot = snapshot
        return state

    # --- ready → running_* への自動遷移 ---
    if state.state == HighLevelState.READY:
        if t - state.state_entered_at >= ready_s:
            new_hs = _pace_to_state(state.pace)
            _enter(state, new_hs, t)

    # --- スプリットイベントで impulse ウィンドウを更新 ---
    from app.domain.events import SPLIT_BAD, SPLIT_CHANGED, SPLIT_GOOD, SPLIT_UNDO

    if SPLIT_CHANGED in event_names or SPLIT_UNDO in event_names:
        state.impulse_until = t + split_priority_s

    # --- pace 変化のデバウンス ---
    if snapshot is not None and state.state in (
        HighLevelState.RUNNING_NEUTRAL,
        HighLevelState.RUNNING_AHEAD,
        HighLevelState.RUNNING_BEHIND,
        HighLevelState.READY,
    ):
        current_pace = classify_pace(
            snapshot.delta if snapshot else None, th
        )

        if current_pace != state.pace:
            if state.pending_pace != current_pace:
                # 新しい pace 変化を記録
                state.pending_pace = current_pace
                state.pace_changed_at = t
            elif t - state.pace_changed_at >= debounce_s:
                # デバウンス経過: pace を確定
                state.pace = current_pace
                state.pending_pace = None
                if state.state != HighLevelState.READY:
                    _enter(state, _pace_to_state(state.pace), t)
        else:
            state.pending_pace = None

    # --- running 状態中の通常更新 ---
    if state.state in (
        HighLevelState.RUNNING_NEUTRAL,
        HighLevelState.RUNNING_AHEAD,
        HighLevelState.RUNNING_BEHIND,
    ):
        expected = _pace_to_state(state.pace)
        if state.state != expected:
            _enter(state, expected, t)

    state.last_snapshot = snapshot
    return state


def set_disconnected(state: RuntimeState, t: float | None = None) -> RuntimeState:
    """接続断を記録する。"""
    if t is None:
        t = _now()
    _enter(state, HighLevelState.DISCONNECTED, t)
    return state


def _enter(state: RuntimeState, new_state: HighLevelState, t: float) -> None:
    state.state = new_state
    state.state_entered_at = t


def _pace_to_state(pace: PaceBucket) -> HighLevelState:
    return {
        PaceBucket.AHEAD: HighLevelState.RUNNING_AHEAD,
        PaceBucket.NEUTRAL: HighLevelState.RUNNING_NEUTRAL,
        PaceBucket.BEHIND: HighLevelState.RUNNING_BEHIND,
    }[pace]
