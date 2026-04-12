"""AmbientMotionController のユニットテスト。"""
from __future__ import annotations

import math

import pytest

from app.config import AmbientConfig
from app.domain.events import InternalEvent, SPLIT_BAD, SPLIT_GOOD
from app.domain.state_machine import RuntimeState
from app.motions.ambient import AmbientMotionController, HeadTarget, _BASE_POSES, _clamp
from app.types import HighLevelState


def _make_cfg(**kwargs) -> AmbientConfig:
    defaults = dict(
        enabled=True,
        strength=1.0,
        update_duration=0.4,
        breathing_amplitude=2.5,
        breathing_period=4.0,
        glance_interval_min=30.0,
        glance_interval_max=60.0,
        glance_amplitude=5.0,
        glance_return_duration=1.2,
        running_sway_amplitude=1.5,
        running_sway_period=6.0,
        tilt_amplitude=3.0,
        tilt_period=8.0,
        afterglow_duration=3.0,
        sag_duration=2.0,
        post_impulse_pause=0.8,
    )
    defaults.update(kwargs)
    return AmbientConfig(**defaults)


def _make_state(state: HighLevelState = HighLevelState.IDLE) -> RuntimeState:
    rs = RuntimeState()
    rs.state = state
    return rs


# --- HeadTarget dataclass ---

def test_head_target_defaults():
    t = HeadTarget()
    assert t.pitch == 0.0
    assert t.roll == 0.0
    assert t.yaw == 0.0
    assert t.antenna_l == 0.2
    assert t.antenna_r == 0.2
    assert t.duration == 0.4


# --- _clamp ---

def test_clamp_within():
    assert _clamp(5.0, 0.0, 10.0) == 5.0


def test_clamp_low():
    assert _clamp(-5.0, 0.0, 10.0) == 0.0


def test_clamp_high():
    assert _clamp(15.0, 0.0, 10.0) == 10.0


# --- compute_target: strength=0 → base pose ---

@pytest.mark.parametrize("hs", list(HighLevelState))
def test_compute_target_zero_strength_returns_base(hs: HighLevelState):
    cfg = _make_cfg(strength=0.0)
    ctrl = AmbientMotionController(cfg)
    state = _make_state(hs)
    target = ctrl.compute_target(state, t=0.0)

    base = _BASE_POSES[hs]
    assert target.pitch == pytest.approx(base.pitch, abs=0.01)
    assert target.roll == pytest.approx(base.roll, abs=0.01)
    assert target.yaw == pytest.approx(base.yaw, abs=0.01)
    assert target.antenna_l == pytest.approx(base.antenna_l, abs=0.01)
    assert target.antenna_r == pytest.approx(base.antenna_r, abs=0.01)


# --- compute_target: DISCONNECTED / SAFE_MODE → base pose (no offset even with strength=1) ---

@pytest.mark.parametrize("hs", [HighLevelState.DISCONNECTED, HighLevelState.SAFE_MODE])
def test_compute_target_disconnected_no_offset(hs: HighLevelState):
    cfg = _make_cfg(strength=1.0, breathing_amplitude=10.0)
    ctrl = AmbientMotionController(cfg)
    state = _make_state(hs)
    # Try multiple time points; none should deviate from base
    base = _BASE_POSES[hs]
    for t in (0.0, 1.0, 2.0, 10.0):
        target = ctrl.compute_target(state, t=t)
        assert target.pitch == pytest.approx(base.pitch, abs=0.01)
        assert target.yaw == pytest.approx(base.yaw, abs=0.01)


# --- idle_breathing ---

def test_breathing_oscillates_in_idle():
    cfg = _make_cfg(strength=1.0, breathing_amplitude=2.5, breathing_period=4.0)
    ctrl = AmbientMotionController(cfg)
    state = _make_state(HighLevelState.IDLE)
    base_pitch = _BASE_POSES[HighLevelState.IDLE].pitch

    # Collect pitch values over one cycle
    pitches = [
        ctrl.compute_target(state, t=i * 0.1).pitch - base_pitch
        for i in range(50)
    ]
    # Offsets should have both positive and negative values (oscillation)
    assert max(pitches) > 0.5
    assert min(pitches) < -0.5


def test_breathing_amplitude_respected():
    amplitude = 3.0
    cfg = _make_cfg(strength=1.0, breathing_amplitude=amplitude, breathing_period=4.0)
    ctrl = AmbientMotionController(cfg)
    state = _make_state(HighLevelState.IDLE)
    base_pitch = _BASE_POSES[HighLevelState.IDLE].pitch

    pitches = [
        ctrl.compute_target(state, t=i * 0.05).pitch - base_pitch
        for i in range(200)
    ]
    # Max excursion should not exceed amplitude (with a small tolerance for modulation)
    assert max(pitches) <= amplitude * 1.25
    assert min(pitches) >= -amplitude * 1.25


def test_breathing_not_in_running_state():
    """RUNNING 中は breathing offset が IDLE より小さいはず（呼吸は IDLE 限定）。"""
    cfg = _make_cfg(strength=1.0, breathing_amplitude=2.5, breathing_period=4.0)
    ctrl_idle = AmbientMotionController(cfg)
    ctrl_run = AmbientMotionController(cfg)

    idle_state = _make_state(HighLevelState.IDLE)
    run_state = _make_state(HighLevelState.RUNNING_NEUTRAL)
    base_idle = _BASE_POSES[HighLevelState.IDLE].pitch
    base_run = _BASE_POSES[HighLevelState.RUNNING_NEUTRAL].pitch

    idle_offsets = [
        abs(ctrl_idle.compute_target(idle_state, t=i * 0.1).pitch - base_idle)
        for i in range(50)
    ]
    run_offsets = [
        abs(ctrl_run.compute_target(run_state, t=i * 0.1).pitch - base_run)
        for i in range(50)
    ]
    # IDLE の pitch 変動が RUNNING より大きい
    assert max(idle_offsets) > max(run_offsets)


# --- curiosity_glance ---

def test_glance_does_not_fire_before_min_interval():
    cfg = _make_cfg(
        strength=1.0,
        glance_interval_min=30.0,
        glance_interval_max=60.0,
        glance_amplitude=5.0,
        glance_return_duration=1.2,
    )
    ctrl = AmbientMotionController(cfg)
    state = _make_state(HighLevelState.IDLE)
    base_yaw = _BASE_POSES[HighLevelState.IDLE].yaw

    # t=0 〜 29s: グランスは発火しないはず
    for i in range(29 * 10):
        t = i * 0.1
        target = ctrl.compute_target(state, t=t)
        assert abs(target.yaw - base_yaw) < 0.01, f"Unexpected glance at t={t:.1f}"


def test_glance_fires_after_min_interval():
    cfg = _make_cfg(
        strength=1.0,
        glance_interval_min=5.0,
        glance_interval_max=6.0,
        glance_amplitude=5.0,
        glance_return_duration=1.2,
    )
    ctrl = AmbientMotionController(cfg)
    state = _make_state(HighLevelState.IDLE)
    base_yaw = _BASE_POSES[HighLevelState.IDLE].yaw

    # t=0 でタイマーを初期化してから、5〜8s の間にグランスが発火するはずを確認
    ctrl.compute_target(state, t=0.0)  # 初期化トリガー
    yaw_offsets = [
        abs(ctrl.compute_target(state, t=t).yaw - base_yaw)
        for t in [5.0 + i * 0.1 for i in range(30)]
    ]
    assert max(yaw_offsets) > 0.1, "Glance never fired after min interval"


def test_glance_peak_amplitude_within_bound():
    cfg = _make_cfg(
        strength=1.0,
        glance_interval_min=5.0,
        glance_interval_max=6.0,
        glance_amplitude=5.0,
        glance_return_duration=1.2,
    )
    ctrl = AmbientMotionController(cfg)
    state = _make_state(HighLevelState.IDLE)
    base_yaw = _BASE_POSES[HighLevelState.IDLE].yaw

    yaw_values = [
        ctrl.compute_target(state, t=t).yaw - base_yaw
        for t in [i * 0.05 for i in range(300)]
    ]
    assert max(yaw_values) <= 5.5  # amplitude + tiny tolerance
    assert min(yaw_values) >= -5.5


# --- running_sway ---

def test_running_sway_active_in_running_states():
    cfg = _make_cfg(
        strength=1.0,
        running_sway_amplitude=1.5,
        running_sway_period=6.0,
        glance_interval_min=9999.0,
        glance_interval_max=10000.0,
    )
    for hs in (
        HighLevelState.RUNNING_NEUTRAL,
        HighLevelState.RUNNING_AHEAD,
        HighLevelState.RUNNING_BEHIND,
    ):
        ctrl = AmbientMotionController(cfg)
        state = _make_state(hs)
        base_pitch = _BASE_POSES[hs].pitch

        pitches = [
            ctrl.compute_target(state, t=i * 0.5).pitch - base_pitch
            for i in range(20)
        ]
        assert max(abs(p) for p in pitches) > 0.1, f"No sway in {hs}"


def test_running_sway_smaller_than_idle_breathing():
    """running_sway は idle_breathing より振れ幅が小さい。"""
    cfg = _make_cfg(
        strength=1.0,
        breathing_amplitude=2.5,
        breathing_period=4.0,
        running_sway_amplitude=1.5,
        running_sway_period=6.0,
        glance_interval_min=9999.0,
        glance_interval_max=10000.0,
    )
    idle_ctrl = AmbientMotionController(cfg)
    run_ctrl = AmbientMotionController(cfg)
    idle_state = _make_state(HighLevelState.IDLE)
    run_state = _make_state(HighLevelState.RUNNING_NEUTRAL)

    idle_max = max(
        abs(idle_ctrl.compute_target(idle_state, t=i * 0.1).pitch - _BASE_POSES[HighLevelState.IDLE].pitch)
        for i in range(100)
    )
    run_max = max(
        abs(run_ctrl.compute_target(run_state, t=i * 0.1).pitch - _BASE_POSES[HighLevelState.RUNNING_NEUTRAL].pitch)
        for i in range(100)
    )
    assert idle_max > run_max


def test_running_sway_not_in_idle():
    """IDLE 状態では running_sway が乗らないこと（breathing のみ）。"""
    cfg = _make_cfg(
        strength=0.0,  # strength=0 で breathing も sway もゼロ
    )
    ctrl = AmbientMotionController(cfg)
    state = _make_state(HighLevelState.IDLE)
    base_pitch = _BASE_POSES[HighLevelState.IDLE].pitch

    for i in range(20):
        target = ctrl.compute_target(state, t=i * 0.5)
        assert target.pitch == pytest.approx(base_pitch, abs=0.01)


# --- thinking_tilt ---

def test_thinking_tilt_active_when_behind():
    cfg = _make_cfg(strength=1.0, tilt_amplitude=3.0, tilt_period=8.0)
    ctrl = AmbientMotionController(cfg)
    state = _make_state(HighLevelState.RUNNING_BEHIND)
    base_roll = _BASE_POSES[HighLevelState.RUNNING_BEHIND].roll

    rolls = [
        ctrl.compute_target(state, t=i * 0.5).roll - base_roll
        for i in range(20)
    ]
    assert max(abs(r) for r in rolls) > 0.1


def test_thinking_tilt_zero_when_neutral():
    cfg = _make_cfg(strength=1.0, tilt_amplitude=3.0, tilt_period=8.0,
                    glance_interval_min=9999.0, glance_interval_max=10000.0)
    ctrl = AmbientMotionController(cfg)
    state = _make_state(HighLevelState.RUNNING_NEUTRAL)
    base_roll = _BASE_POSES[HighLevelState.RUNNING_NEUTRAL].roll

    # RUNNING_NEUTRAL では tilt なし
    for i in range(20):
        target = ctrl.compute_target(state, t=i * 0.5)
        assert abs(target.roll - base_roll) < 0.01


# --- afterglow ---

def test_afterglow_raises_antennas_after_good_split():
    cfg = _make_cfg(strength=1.0, afterglow_duration=3.0,
                    glance_interval_min=9999.0, glance_interval_max=10000.0)
    ctrl = AmbientMotionController(cfg)
    state = _make_state(HighLevelState.RUNNING_NEUTRAL)
    base = _BASE_POSES[HighLevelState.RUNNING_NEUTRAL]

    event = InternalEvent(name=SPLIT_GOOD, at=10.0)
    ctrl.notify_events([event], t=10.0)

    # アフターグロー直後: アンテナが上がるはず
    target = ctrl.compute_target(state, t=10.1)
    assert target.antenna_l > base.antenna_l
    assert target.antenna_r > base.antenna_r


def test_afterglow_fades_over_duration():
    cfg = _make_cfg(strength=1.0, afterglow_duration=3.0,
                    glance_interval_min=9999.0, glance_interval_max=10000.0)
    ctrl = AmbientMotionController(cfg)
    state = _make_state(HighLevelState.RUNNING_NEUTRAL)
    base = _BASE_POSES[HighLevelState.RUNNING_NEUTRAL]

    event = InternalEvent(name=SPLIT_GOOD, at=10.0)
    ctrl.notify_events([event], t=10.0)

    # アフターグロー終了後: ベースポーズに戻るはず
    target = ctrl.compute_target(state, t=14.0)  # 3s + 1s margin
    assert target.antenna_l == pytest.approx(base.antenna_l, abs=0.01)
    assert target.antenna_r == pytest.approx(base.antenna_r, abs=0.01)


# --- sag ---

def test_sag_drops_antennas_after_bad_split():
    cfg = _make_cfg(strength=1.0, sag_duration=2.0,
                    glance_interval_min=9999.0, glance_interval_max=10000.0)
    ctrl = AmbientMotionController(cfg)
    state = _make_state(HighLevelState.RUNNING_NEUTRAL)
    base = _BASE_POSES[HighLevelState.RUNNING_NEUTRAL]

    event = InternalEvent(name=SPLIT_BAD, at=10.0)
    ctrl.notify_events([event], t=10.0)

    target = ctrl.compute_target(state, t=10.1)
    # サグ中: アンテナが下がる、ピッチが増加（うつむき）
    assert target.antenna_l < base.antenna_l
    assert target.antenna_r < base.antenna_r
    assert target.pitch > base.pitch


def test_sag_cancelled_by_good_split():
    cfg = _make_cfg(strength=1.0, sag_duration=5.0, afterglow_duration=3.0,
                    glance_interval_min=9999.0, glance_interval_max=10000.0)
    ctrl = AmbientMotionController(cfg)
    state = _make_state(HighLevelState.RUNNING_NEUTRAL)
    base = _BASE_POSES[HighLevelState.RUNNING_NEUTRAL]

    bad_event = InternalEvent(name=SPLIT_BAD, at=10.0)
    ctrl.notify_events([bad_event], t=10.0)

    # その直後に SPLIT_GOOD が来てサグをキャンセル
    good_event = InternalEvent(name=SPLIT_GOOD, at=10.5)
    ctrl.notify_events([good_event], t=10.5)

    target = ctrl.compute_target(state, t=10.6)
    # サグはキャンセルされているので antenna は base より下がらない
    assert target.antenna_l >= base.antenna_l


# --- 安全クランプ ---

def test_safety_clamp_pitch():
    """極端な amplitude でもクランプ範囲に収まること。"""
    cfg = _make_cfg(strength=10.0, breathing_amplitude=100.0, breathing_period=0.1)
    ctrl = AmbientMotionController(cfg)
    state = _make_state(HighLevelState.IDLE)

    for i in range(50):
        target = ctrl.compute_target(state, t=i * 0.01)
        assert target.pitch >= -20.0
        assert target.pitch <= 25.0


def test_safety_clamp_yaw():
    cfg = _make_cfg(
        strength=10.0,
        glance_amplitude=100.0,
        glance_interval_min=0.0,
        glance_interval_max=0.1,
        glance_return_duration=0.5,
    )
    ctrl = AmbientMotionController(cfg)
    state = _make_state(HighLevelState.IDLE)

    for i in range(100):
        target = ctrl.compute_target(state, t=i * 0.05)
        assert target.yaw >= -12.0
        assert target.yaw <= 12.0


def test_safety_clamp_antenna():
    cfg = _make_cfg(strength=10.0, afterglow_duration=100.0,
                    glance_interval_min=9999.0, glance_interval_max=10000.0)
    ctrl = AmbientMotionController(cfg)
    state = _make_state(HighLevelState.RUNNING_NEUTRAL)

    event = InternalEvent(name=SPLIT_GOOD, at=0.0)
    ctrl.notify_events([event], t=0.0)

    for i in range(20):
        target = ctrl.compute_target(state, t=i * 0.1)
        assert 0.0 <= target.antenna_l <= 1.0
        assert 0.0 <= target.antenna_r <= 1.0
