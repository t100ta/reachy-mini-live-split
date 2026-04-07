from __future__ import annotations

import logging
import random

from app.clock import now as _now
from app.config import AppConfig
from app.domain.events import (
    InternalEvent,
    PACE_AHEAD,
    PACE_BEHIND,
    RUN_FINISHED,
    RUN_RESET,
    RUN_STARTED,
    SPLIT_BAD,
    SPLIT_GOOD,
    SPLIT_UNDO,
)
from app.domain.state_machine import RuntimeState
from app.motions.catalog import CATALOG, IDLE_VARIATIONS, MotionDef
from app.motions.cooldown import CooldownTracker
from app.types import HighLevelState

logger = logging.getLogger(__name__)

# 最後にアイドルバリエーションを再生した時刻（モジュールレベルで保持）
_last_idle_variation_at: float = 0.0

# アイドルバリエーションを挟む対象の状態
_IDLE_VARIATION_STATES = frozenset({
    HighLevelState.IDLE,
    HighLevelState.RUNNING_NEUTRAL,
    HighLevelState.RUNNING_AHEAD,
    HighLevelState.RUNNING_BEHIND,
})

# 状態 → 継続ポーズのマッピング
_STATE_TO_POSE: dict[HighLevelState, str] = {
    HighLevelState.IDLE: "idle_pose",
    HighLevelState.READY: "ready_pose",
    HighLevelState.RUNNING_NEUTRAL: "running_neutral_pose",
    HighLevelState.RUNNING_AHEAD: "running_ahead_pose",
    HighLevelState.RUNNING_BEHIND: "running_behind_pose",
    HighLevelState.FINISHED: "idle_pose",
    HighLevelState.DISCONNECTED: "disconnected_pose",
    HighLevelState.SAFE_MODE: "disconnected_pose",
    HighLevelState.PAUSED: "running_neutral_pose",
}

# イベント → インパルスモーションのマッピング（優先度順）
_EVENT_TO_IMPULSE: list[tuple[str, str]] = [
    (RUN_FINISHED, "finish_celebrate"),
    (RUN_RESET, "reset_sigh"),
    (SPLIT_GOOD, "split_good_nod"),
    (SPLIT_BAD, "split_bad_droop"),
    (SPLIT_UNDO, "split_bad_droop"),
    (RUN_STARTED, "ready_pose"),
]


def select_motion(
    state: RuntimeState,
    events: list[InternalEvent],
    cooldown: CooldownTracker,
    cfg: AppConfig,
    t: float | None = None,
) -> MotionDef | None:
    """
    現在の状態とイベントをもとに実行するモーションを選択して返す。
    クールダウン中や無効なモーションの場合は None を返す。
    """
    if t is None:
        t = _now()

    event_names = {e.name for e in events}

    # 1. safe_mode / disconnected → 固定ポーズ
    if state.state in (HighLevelState.SAFE_MODE, HighLevelState.DISCONNECTED):
        return _get_if_available("disconnected_pose", cooldown, cfg, t)

    # 2. インパルスウィンドウ内のイベント反応（優先度高）
    if t <= state.impulse_until:
        for event_name, motion_name in _EVENT_TO_IMPULSE:
            if event_name in event_names:
                return _get_if_available(motion_name, cooldown, cfg, t)

    # run_finished / run_reset は impulse_until に関係なく常に反応
    for event_name, motion_name in [
        (RUN_FINISHED, "finish_celebrate"),
        (RUN_RESET, "reset_sigh"),
    ]:
        if event_name in event_names:
            return _get_if_available(motion_name, cooldown, cfg, t)

    # 3. アイドルバリエーション（一定時間操作なしの場合にランダム再生）
    if state.state in _IDLE_VARIATION_STATES and t > state.impulse_until:
        variation = _maybe_idle_variation(cooldown, cfg, t)
        if variation is not None:
            return variation

    # 4. 継続ポーズ
    pose_name = _STATE_TO_POSE.get(state.state, "idle_pose")
    return _get_if_available(pose_name, cooldown, cfg, t)


def _maybe_idle_variation(
    cooldown: CooldownTracker,
    cfg: AppConfig,
    t: float,
) -> MotionDef | None:
    """インターバルが経過していればランダムなアイドルバリエーションを返す。"""
    global _last_idle_variation_at
    interval_s = cfg.thresholds.idle_variation_interval_ms / 1000.0
    if (t - _last_idle_variation_at) < interval_s:
        return None

    candidates = [
        v for v in IDLE_VARIATIONS
        if cooldown.can_execute(v.name, is_impulse=True, t=t)
        and (cfg.motions.get(v.name) is None or cfg.motions[v.name].enabled)
    ]
    if not candidates:
        return None

    chosen = random.choice(candidates)
    _last_idle_variation_at = t
    logger.debug("アイドルバリエーション選択: %s", chosen.name)
    return chosen


def _get_if_available(
    motion_name: str,
    cooldown: CooldownTracker,
    cfg: AppConfig,
    t: float,
) -> MotionDef | None:
    """モーションが有効でクールダウン中でなければ返す。"""
    motion_cfg = cfg.motions.get(motion_name)
    if motion_cfg is not None and not motion_cfg.enabled:
        logger.debug("Motion %s は無効化されています", motion_name)
        return None

    motion = CATALOG.get(motion_name)
    if motion is None:
        logger.warning("Motion %s はカタログに存在しません", motion_name)
        return None

    if not cooldown.can_execute(motion_name, is_impulse=motion.is_impulse, t=t):
        logger.debug("Motion %s はクールダウン中です", motion_name)
        return None

    return motion
