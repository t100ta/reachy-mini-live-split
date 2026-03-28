import pytest
from app.config import AppConfig
from app.domain.events import InternalEvent, RUN_FINISHED, RUN_RESET, RUN_STARTED
from app.domain.state_machine import RuntimeState, set_disconnected, transition
from app.livesplit.snapshot import LiveSplitSnapshot
from app.types import HighLevelState, PaceBucket


def make_state(**kwargs) -> RuntimeState:
    s = RuntimeState()
    for k, v in kwargs.items():
        setattr(s, k, v)
    return s


def snap(phase="Running", split_index=0, delta=None):
    return LiveSplitSnapshot(
        captured_at=0.0,
        timer_phase=phase,
        split_index=split_index,
        current_split_name=None,
        current_time=None,
        delta=delta,
        attempt_count=1,
    )


def event(name: str) -> InternalEvent:
    return InternalEvent(name=name, at=0.0)


@pytest.fixture
def cfg():
    return AppConfig()


def test_run_started_transitions_to_ready(cfg):
    state = RuntimeState()
    transition(state, [event(RUN_STARTED)], snap(), cfg, t=100.0)
    assert state.state == HighLevelState.READY


def test_ready_transitions_to_running_after_duration(cfg):
    state = RuntimeState()
    state.state = HighLevelState.READY
    state.state_entered_at = 0.0
    # ready_duration_ms = 1200 = 1.2s; pass t = 2.0 > 1.2
    transition(state, [], snap(), cfg, t=2.0)
    assert state.state in (
        HighLevelState.RUNNING_NEUTRAL,
        HighLevelState.RUNNING_AHEAD,
        HighLevelState.RUNNING_BEHIND,
    )


def test_run_finished_transitions_to_finished(cfg):
    state = RuntimeState()
    state.state = HighLevelState.RUNNING_NEUTRAL
    transition(state, [event(RUN_FINISHED)], snap("Ended"), cfg, t=100.0)
    assert state.state == HighLevelState.FINISHED


def test_run_reset_transitions_to_idle(cfg):
    state = RuntimeState()
    state.state = HighLevelState.RUNNING_NEUTRAL
    transition(state, [event(RUN_RESET)], snap("NotRunning"), cfg, t=100.0)
    assert state.state == HighLevelState.IDLE


def test_set_disconnected(cfg):
    state = RuntimeState()
    set_disconnected(state, t=100.0)
    assert state.state == HighLevelState.DISCONNECTED


def test_disconnected_to_idle_on_reconnect(cfg):
    state = RuntimeState()
    state.state = HighLevelState.DISCONNECTED
    transition(state, [], snap(), cfg, t=100.0)
    assert state.state == HighLevelState.IDLE
