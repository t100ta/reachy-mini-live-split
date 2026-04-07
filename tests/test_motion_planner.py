import pytest
import app.motions.planner as planner_module
from app.config import AppConfig
from app.domain.events import InternalEvent, RUN_FINISHED, RUN_RESET, RUN_STARTED, SPLIT_BAD, SPLIT_GOOD
from app.domain.state_machine import RuntimeState
from app.motions.catalog import IDLE_VARIATIONS, CATALOG
from app.motions.cooldown import CooldownTracker
from app.motions.planner import select_motion
from app.types import HighLevelState

_IDLE_VARIATION_NAMES = frozenset(m.name for m in IDLE_VARIATIONS)


def event(name: str) -> InternalEvent:
    return InternalEvent(name=name, at=0.0)


@pytest.fixture
def cfg():
    return AppConfig()


@pytest.fixture(autouse=True)
def reset_idle_timer():
    """既存テストにアイドルバリエーションが干渉しないよう、タイマーを大きい値で初期化する。"""
    planner_module._last_idle_variation_at = 99_999.0
    yield
    planner_module._last_idle_variation_at = 0.0


def make_state(state: HighLevelState, impulse_until: float = 0.0) -> RuntimeState:
    s = RuntimeState()
    s.state = state
    s.impulse_until = impulse_until
    return s


def test_idle_returns_idle_pose(cfg):
    state = make_state(HighLevelState.IDLE)
    cooldown = CooldownTracker()
    motion = select_motion(state, [], cooldown, cfg, t=100.0)
    assert motion is not None
    assert motion.name == "idle_pose"


def test_running_neutral_returns_pose(cfg):
    state = make_state(HighLevelState.RUNNING_NEUTRAL)
    cooldown = CooldownTracker()
    motion = select_motion(state, [], cooldown, cfg, t=100.0)
    assert motion is not None
    assert motion.name == "running_neutral_pose"


def test_split_good_returns_nod_in_impulse_window(cfg):
    state = make_state(HighLevelState.RUNNING_NEUTRAL, impulse_until=200.0)
    cooldown = CooldownTracker()
    motion = select_motion(state, [event(SPLIT_GOOD)], cooldown, cfg, t=100.0)
    assert motion is not None
    assert motion.name == "split_good_nod"


def test_split_bad_returns_droop_in_impulse_window(cfg):
    state = make_state(HighLevelState.RUNNING_NEUTRAL, impulse_until=200.0)
    cooldown = CooldownTracker()
    motion = select_motion(state, [event(SPLIT_BAD)], cooldown, cfg, t=100.0)
    assert motion is not None
    assert motion.name == "split_bad_droop"


def test_reset_sigh_on_run_reset(cfg):
    state = make_state(HighLevelState.RUNNING_NEUTRAL)
    cooldown = CooldownTracker()
    motion = select_motion(state, [event(RUN_RESET)], cooldown, cfg, t=100.0)
    assert motion is not None
    assert motion.name == "reset_sigh"


def test_finish_celebrate_on_run_finished(cfg):
    state = make_state(HighLevelState.FINISHED)
    cooldown = CooldownTracker()
    motion = select_motion(state, [event(RUN_FINISHED)], cooldown, cfg, t=100.0)
    assert motion is not None
    assert motion.name == "finish_celebrate"


def test_pose_cooldown_prevents_same_motion(cfg):
    """継続ポーズは pose_cooldown_ms 中は再実行されない。"""
    state = make_state(HighLevelState.IDLE)
    cooldown = CooldownTracker(pose_cooldown_ms=2000)
    t = 100.0
    motion = select_motion(state, [], cooldown, cfg, t=t)
    assert motion is not None
    cooldown.record(motion.name, t)
    # 0.5秒後はまだクールダウン中
    motion2 = select_motion(state, [], cooldown, cfg, t=t + 0.5)
    assert motion2 is None


def test_impulse_cooldown_is_short(cfg):
    """インパルスモーションは 500ms 経過後に再実行できる。"""
    state = make_state(HighLevelState.RUNNING_NEUTRAL, impulse_until=200.0)
    cooldown = CooldownTracker(impulse_cooldown_ms=500)
    t = 100.0
    motion = select_motion(state, [event(SPLIT_GOOD)], cooldown, cfg, t=t)
    assert motion is not None
    assert motion.name == "split_good_nod"
    cooldown.record(motion.name, t)
    # 0.3秒後はまだクールダウン中
    motion2 = select_motion(state, [event(SPLIT_GOOD)], cooldown, cfg, t=t + 0.3)
    assert motion2 is None
    # 0.6秒後は実行可能
    motion3 = select_motion(state, [event(SPLIT_GOOD)], cooldown, cfg, t=t + 0.6)
    assert motion3 is not None
    assert motion3.name == "split_good_nod"


def test_disconnected_returns_disconnected_pose(cfg):
    state = make_state(HighLevelState.DISCONNECTED)
    cooldown = CooldownTracker()
    motion = select_motion(state, [], cooldown, cfg, t=100.0)
    assert motion is not None
    assert motion.name == "disconnected_pose"


# ---------------------------------------------------------------------------
# アイドルバリエーション
# ---------------------------------------------------------------------------

class TestIdleVariationCatalog:
    def test_variations_exist_in_catalog(self):
        assert len(IDLE_VARIATIONS) >= 3
        for m in IDLE_VARIATIONS:
            assert m.name in CATALOG, f"{m.name} がカタログに存在しない"

    def test_variations_are_impulse(self):
        for m in IDLE_VARIATIONS:
            assert m.is_impulse is True, f"{m.name} は is_impulse=True であるべき"
            assert m.duration_ms > 0, f"{m.name} の duration_ms は正であるべき"

    def test_default_interval_is_45s(self):
        assert AppConfig().thresholds.idle_variation_interval_ms == 45_000


class TestIdleVariationTrigger:
    def test_fires_after_interval(self, cfg):
        planner_module._last_idle_variation_at = 0.0
        cfg.thresholds.idle_variation_interval_ms = 5_000
        state = make_state(HighLevelState.RUNNING_NEUTRAL)
        motion = select_motion(state, [], CooldownTracker(), cfg, t=10.0)
        assert motion is not None
        assert motion.name in _IDLE_VARIATION_NAMES

    def test_does_not_fire_before_interval(self, cfg):
        planner_module._last_idle_variation_at = 0.0
        cfg.thresholds.idle_variation_interval_ms = 30_000
        state = make_state(HighLevelState.RUNNING_NEUTRAL)
        motion = select_motion(state, [], CooldownTracker(), cfg, t=10.0)
        assert motion is not None
        assert motion.name == "running_neutral_pose"

    def test_fires_in_idle_state(self, cfg):
        planner_module._last_idle_variation_at = 0.0
        cfg.thresholds.idle_variation_interval_ms = 1
        state = make_state(HighLevelState.IDLE)
        motion = select_motion(state, [], CooldownTracker(), cfg, t=100.0)
        assert motion is not None
        assert motion.name in _IDLE_VARIATION_NAMES

    def test_fires_while_ahead(self, cfg):
        planner_module._last_idle_variation_at = 0.0
        cfg.thresholds.idle_variation_interval_ms = 1
        state = make_state(HighLevelState.RUNNING_AHEAD)
        motion = select_motion(state, [], CooldownTracker(), cfg, t=100.0)
        assert motion is not None
        assert motion.name in _IDLE_VARIATION_NAMES

    def test_fires_while_behind(self, cfg):
        planner_module._last_idle_variation_at = 0.0
        cfg.thresholds.idle_variation_interval_ms = 1
        state = make_state(HighLevelState.RUNNING_BEHIND)
        motion = select_motion(state, [], CooldownTracker(), cfg, t=100.0)
        assert motion is not None
        assert motion.name in _IDLE_VARIATION_NAMES


class TestIdleVariationSuppression:
    def test_suppressed_during_impulse_window(self, cfg):
        """インパルスウィンドウ中は発火しない。"""
        planner_module._last_idle_variation_at = 0.0
        cfg.thresholds.idle_variation_interval_ms = 1
        state = make_state(HighLevelState.RUNNING_NEUTRAL, impulse_until=200.0)
        motion = select_motion(state, [], CooldownTracker(), cfg, t=100.0)
        assert motion is None or motion.name not in _IDLE_VARIATION_NAMES

    def test_suppressed_in_finished_state(self, cfg):
        """FINISHED 状態では発火しない。"""
        planner_module._last_idle_variation_at = 0.0
        cfg.thresholds.idle_variation_interval_ms = 1
        state = make_state(HighLevelState.FINISHED)
        motion = select_motion(state, [], CooldownTracker(), cfg, t=100.0)
        assert motion is None or motion.name not in _IDLE_VARIATION_NAMES

    def test_suppressed_in_disconnected_state(self, cfg):
        """DISCONNECTED 状態では発火しない。"""
        planner_module._last_idle_variation_at = 0.0
        cfg.thresholds.idle_variation_interval_ms = 1
        state = make_state(HighLevelState.DISCONNECTED)
        motion = select_motion(state, [], CooldownTracker(), cfg, t=100.0)
        assert motion is not None
        assert motion.name == "disconnected_pose"

    def test_event_takes_priority(self, cfg):
        """インパルスウィンドウ内のイベントはアイドルバリエーションより優先される。"""
        planner_module._last_idle_variation_at = 0.0
        cfg.thresholds.idle_variation_interval_ms = 1
        state = make_state(HighLevelState.RUNNING_NEUTRAL, impulse_until=200.0)
        motion = select_motion(state, [event(SPLIT_GOOD)], CooldownTracker(), cfg, t=100.0)
        assert motion is not None
        assert motion.name == "split_good_nod"

    def test_run_reset_takes_priority(self, cfg):
        """RUN_RESET はインターバル経過後でも優先される。"""
        planner_module._last_idle_variation_at = 0.0
        cfg.thresholds.idle_variation_interval_ms = 1
        state = make_state(HighLevelState.RUNNING_NEUTRAL)
        motion = select_motion(state, [event(RUN_RESET)], CooldownTracker(), cfg, t=100.0)
        assert motion is not None
        assert motion.name == "reset_sigh"


class TestIdleVariationTimer:
    def test_timer_resets_after_fire(self, cfg):
        """一度発火した後はタイマーがリセットされ、すぐに再発火しない。"""
        planner_module._last_idle_variation_at = 0.0
        cfg.thresholds.idle_variation_interval_ms = 5_000
        state = make_state(HighLevelState.RUNNING_NEUTRAL)
        cooldown = CooldownTracker()
        t = 10.0

        motion = select_motion(state, [], cooldown, cfg, t=t)
        assert motion is not None and motion.name in _IDLE_VARIATION_NAMES
        cooldown.record(motion.name, t)

        # 直後（インターバル未満）は再発火しない
        motion2 = select_motion(state, [], cooldown, cfg, t=t + 0.5)
        assert motion2 is None or motion2.name not in _IDLE_VARIATION_NAMES

    def test_fires_again_after_second_interval(self, cfg):
        """2回目のインターバル経過後に再度発火する。"""
        planner_module._last_idle_variation_at = 0.0
        cfg.thresholds.idle_variation_interval_ms = 5_000
        state = make_state(HighLevelState.RUNNING_NEUTRAL)
        cooldown = CooldownTracker()
        t = 10.0

        motion1 = select_motion(state, [], cooldown, cfg, t=t)
        assert motion1 is not None and motion1.name in _IDLE_VARIATION_NAMES
        cooldown.record(motion1.name, t)

        # インターバルが再び経過したら発火する
        motion2 = select_motion(state, [], cooldown, cfg, t=t + 6.0)
        assert motion2 is not None
        assert motion2.name in _IDLE_VARIATION_NAMES
