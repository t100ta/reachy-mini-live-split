"""アンビエントモーション機構。

待機中・ラン中にベースポーズへ重ねる微小動作を生成する。
Impulse モーション（イベントリアクション）とは独立して動作し、
毎ループ goto_target() ターゲットとして executor へ渡す。
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.types import HighLevelState

if TYPE_CHECKING:
    from app.config import AmbientConfig
    from app.domain.events import InternalEvent
    from app.domain.state_machine import RuntimeState


@dataclass
class HeadTarget:
    """goto_ambient() へ渡すターゲット姿勢。角度は degree 単位。"""

    pitch: float = 0.0
    roll: float = 0.0
    yaw: float = 0.0
    antenna_l: float = 0.2
    antenna_r: float = 0.2
    duration: float = 0.4


# HighLevelState → ベースポーズ（real_executor.py の dispatch と同期すること）
_BASE_POSES: dict[HighLevelState, HeadTarget] = {
    HighLevelState.IDLE:            HeadTarget(pitch=0,   antenna_l=0.2,  antenna_r=0.2),
    HighLevelState.READY:           HeadTarget(pitch=-8,  antenna_l=0.5,  antenna_r=0.5),
    HighLevelState.RUNNING_NEUTRAL: HeadTarget(pitch=0,   antenna_l=0.3,  antenna_r=0.3),
    HighLevelState.RUNNING_AHEAD:   HeadTarget(pitch=-10, antenna_l=0.7,  antenna_r=0.7),
    HighLevelState.RUNNING_BEHIND:  HeadTarget(pitch=12,  antenna_l=0.05, antenna_r=0.05),
    HighLevelState.FINISHED:        HeadTarget(pitch=0,   antenna_l=0.2,  antenna_r=0.2),
    HighLevelState.PAUSED:          HeadTarget(pitch=0,   antenna_l=0.3,  antenna_r=0.3),
    HighLevelState.DISCONNECTED:    HeadTarget(pitch=5,   antenna_l=0.0,  antenna_r=0.0),
    HighLevelState.SAFE_MODE:       HeadTarget(pitch=5,   antenna_l=0.0,  antenna_r=0.0),
}

# アンビエントオフセットを適用する状態
_GLANCE_STATES = frozenset({
    HighLevelState.IDLE,
    HighLevelState.RUNNING_NEUTRAL,
    HighLevelState.RUNNING_AHEAD,
    HighLevelState.RUNNING_BEHIND,
    HighLevelState.FINISHED,
    HighLevelState.PAUSED,
})

# 安全角度クランプ範囲（hardware 限界より狭く設定）
_PITCH_MIN, _PITCH_MAX = -20.0, 25.0
_ROLL_MIN,  _ROLL_MAX  = -8.0,   8.0
_YAW_MIN,   _YAW_MAX   = -12.0, 12.0
_ANT_MIN,   _ANT_MAX   =  0.0,   1.0


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


class AmbientMotionController:
    """状態に応じたアンビエントモーションのターゲット姿勢を計算する。"""

    def __init__(self, cfg: AmbientConfig) -> None:
        self._cfg = cfg
        # glance スケジューラ
        self._next_glance_at: float | None = None  # None = 未初期化
        self._glance_start: float = -1.0           # -1 = グランス未実行
        self._glance_dir: float = 1.0
        # afterglow / sag タイムスタンプ
        self._afterglow_until: float = 0.0
        self._sag_until: float = 0.0

    def notify_events(self, events: list[InternalEvent], t: float) -> None:
        """イベントを受け取り、アフターグロー／サグ状態を更新する。"""
        from app.domain.events import SPLIT_BAD, SPLIT_GOOD

        for event in events:
            if event.name == SPLIT_GOOD:
                self._afterglow_until = t + self._cfg.afterglow_duration
                self._sag_until = 0.0  # 直前のサグをキャンセル
            elif event.name == SPLIT_BAD:
                self._sag_until = t + self._cfg.sag_duration
                self._afterglow_until = 0.0

    def compute_target(self, state: RuntimeState, t: float) -> HeadTarget:
        """現在の状態と時刻からターゲット姿勢を返す。

        DISCONNECTED / SAFE_MODE の場合はベースポーズをそのまま返す。
        """
        base = _BASE_POSES.get(state.state, HeadTarget())

        if state.state in (HighLevelState.DISCONNECTED, HighLevelState.SAFE_MODE):
            return HeadTarget(
                pitch=base.pitch,
                roll=base.roll,
                yaw=base.yaw,
                antenna_l=base.antenna_l,
                antenna_r=base.antenna_r,
                duration=self._cfg.update_duration,
            )

        cfg = self._cfg
        strength = cfg.strength

        dp = 0.0  # pitch オフセット
        dr = 0.0  # roll オフセット
        dy = 0.0  # yaw オフセット
        da_l = 0.0
        da_r = 0.0

        # --- idle_breathing: IDLE 状態のみ ---
        if state.state == HighLevelState.IDLE:
            dp += self._breathing_offset(t) * strength

        # --- running_sway: RUNNING 状態での小さな pitch 揺れ ---
        if state.state in (
            HighLevelState.RUNNING_NEUTRAL,
            HighLevelState.RUNNING_AHEAD,
            HighLevelState.RUNNING_BEHIND,
            HighLevelState.PAUSED,
        ):
            dp += self._running_sway_offset(t) * strength

        # --- curiosity_glance: 複数の状態で有効 ---
        if state.state in _GLANCE_STATES:
            dy += self._glance_offset(t) * strength

        # --- thinking_tilt: RUNNING_BEHIND ---
        if state.state == HighLevelState.RUNNING_BEHIND:
            dr += self._thinking_tilt_offset(t) * strength

        # --- afterglow: SPLIT_GOOD 後の明るさ ---
        if t < self._afterglow_until:
            frac = (self._afterglow_until - t) / cfg.afterglow_duration
            dp += -3.0 * frac * strength        # 少し顔を上げる
            da_l += 0.2 * frac * strength
            da_r += 0.2 * frac * strength

        # --- sag: SPLIT_BAD 後の沈み ---
        if t < self._sag_until:
            frac = (self._sag_until - t) / cfg.sag_duration
            dp += 3.0 * frac * strength         # 少しうつむく
            da_l -= 0.1 * frac * strength
            da_r -= 0.1 * frac * strength

        return HeadTarget(
            pitch=_clamp(base.pitch + dp, _PITCH_MIN, _PITCH_MAX),
            roll=_clamp(base.roll + dr, _ROLL_MIN, _ROLL_MAX),
            yaw=_clamp(base.yaw + dy, _YAW_MIN, _YAW_MAX),
            antenna_l=_clamp(base.antenna_l + da_l, _ANT_MIN, _ANT_MAX),
            antenna_r=_clamp(base.antenna_r + da_r, _ANT_MIN, _ANT_MAX),
            duration=cfg.update_duration,
        )

    # --- 個別オフセット計算 ---

    def _breathing_offset(self, t: float) -> float:
        """idle_breathing: ゆっくりした pitch 振動（呼吸感）。

        周期に緩やかな変調をかけることで機械的すぎる繰り返しを避ける。
        """
        cfg = self._cfg
        T = cfg.breathing_period
        # 3T ごとにわずかに周期が変わるような変調
        modulation = 1.0 + 0.15 * math.sin(t / (T * 3.0))
        effective_T = T * modulation
        return cfg.breathing_amplitude * math.sin(2.0 * math.pi * t / effective_T)

    def _glance_offset(self, t: float) -> float:
        """curiosity_glance: 数十秒に1回、左右どちらかへ小さく頭を振る。"""
        cfg = self._cfg

        # 初回: グランスタイマーを初期化
        if self._next_glance_at is None:
            self._next_glance_at = t + random.uniform(
                cfg.glance_interval_min, cfg.glance_interval_max
            )

        # 新しいグランスを開始するか判定
        if self._glance_start < 0 and t >= self._next_glance_at:
            self._glance_start = t
            self._glance_dir = random.choice([-1.0, 1.0])
            # 次のグランスはこのグランスが終わってから interval 後
            self._next_glance_at = (
                t
                + cfg.glance_return_duration
                + random.uniform(cfg.glance_interval_min, cfg.glance_interval_max)
            )

        # グランス実行中
        if self._glance_start >= 0:
            elapsed = t - self._glance_start
            if elapsed < cfg.glance_return_duration:
                progress = elapsed / cfg.glance_return_duration
                envelope = math.sin(progress * math.pi)  # 0 → 1 → 0
                return cfg.glance_amplitude * envelope * self._glance_dir
            else:
                self._glance_start = -1.0  # 終了

        return 0.0

    def _running_sway_offset(self, t: float) -> float:
        """running_sway: RUNNING 状態でのわずかな pitch 揺れ。

        breathing より小さく遅く、ランの緊張感を表す。
        breathing と周期をずらすため位相オフセットを入れる。
        """
        cfg = self._cfg
        T = cfg.running_sway_period
        modulation = 1.0 + 0.1 * math.sin(t / (T * 4.0))
        effective_T = T * modulation
        return cfg.running_sway_amplitude * math.sin(
            2.0 * math.pi * t / effective_T + math.pi / 3.0
        )

    def _thinking_tilt_offset(self, t: float) -> float:
        """thinking_tilt: RUNNING_BEHIND 時にわずかに首を傾ける。"""
        cfg = self._cfg
        return cfg.tilt_amplitude * math.sin(2.0 * math.pi * t / cfg.tilt_period)
