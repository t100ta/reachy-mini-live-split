import pytest
from app.config import AppConfig
from app.domain.events import InternalEvent, RUN_FINISHED, RUN_RESET, RUN_STARTED, SPLIT_BAD, SPLIT_GOOD
from app.domain.state_machine import RuntimeState
from app.motions.cooldown import CooldownTracker
from app.motions.planner import select_motion
from app.types import HighLevelState


def event(name: str) -> InternalEvent:
    return InternalEvent(name=name, at=0.0)


@pytest.fixture
def cfg():
    return AppConfig()


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
