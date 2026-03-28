import pytest
from app.config import AppConfig
from app.domain.event_detector import detect_events
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
)
from app.livesplit.snapshot import LiveSplitSnapshot


def snap(
    phase="NotRunning",
    split_index=-1,
    delta=None,
    split_name=None,
    attempt_count=1,
    captured_at=0.0,
):
    return LiveSplitSnapshot(
        captured_at=captured_at,
        timer_phase=phase,
        split_index=split_index,
        current_split_name=split_name,
        current_time=None,
        delta=delta,
        attempt_count=attempt_count,
    )


@pytest.fixture
def cfg():
    return AppConfig()


def event_names(events):
    return {e.name for e in events}


# --- run_started ---

def test_run_started(cfg):
    prev = snap("NotRunning")
    curr = snap("Running", split_index=0)
    names = event_names(detect_events(prev, curr, cfg))
    assert RUN_STARTED in names


def test_no_run_started_if_already_running(cfg):
    prev = snap("Running", split_index=0)
    curr = snap("Running", split_index=0)
    names = event_names(detect_events(prev, curr, cfg))
    assert RUN_STARTED not in names


# --- run_reset ---

def test_run_reset_from_running(cfg):
    prev = snap("Running", split_index=1)
    curr = snap("NotRunning")
    names = event_names(detect_events(prev, curr, cfg))
    assert RUN_RESET in names


def test_run_reset_from_paused(cfg):
    prev = snap("Paused", split_index=1)
    curr = snap("NotRunning")
    names = event_names(detect_events(prev, curr, cfg))
    assert RUN_RESET in names


# --- run_finished ---

def test_run_finished(cfg):
    prev = snap("Running", split_index=2)
    curr = snap("Ended", split_index=2)
    names = event_names(detect_events(prev, curr, cfg))
    assert RUN_FINISHED in names


def test_no_duplicate_finished(cfg):
    prev = snap("Ended")
    curr = snap("Ended")
    names = event_names(detect_events(prev, curr, cfg))
    assert RUN_FINISHED not in names


# --- split_changed ---

def test_split_changed(cfg):
    prev = snap("Running", split_index=0, delta=0.0)
    curr = snap("Running", split_index=1, delta=-0.5)
    names = event_names(detect_events(prev, curr, cfg))
    assert SPLIT_CHANGED in names


# --- split_good / split_bad ---

def test_split_good(cfg):
    prev = snap("Running", split_index=0, delta=1.0)
    curr = snap("Running", split_index=1, delta=0.5)
    names = event_names(detect_events(prev, curr, cfg))
    assert SPLIT_GOOD in names
    assert SPLIT_BAD not in names


def test_split_bad(cfg):
    prev = snap("Running", split_index=0, delta=0.5)
    curr = snap("Running", split_index=1, delta=1.5)
    names = event_names(detect_events(prev, curr, cfg))
    assert SPLIT_BAD in names
    assert SPLIT_GOOD not in names


# --- pace ---

def test_pace_ahead(cfg):
    prev = snap("Running", split_index=0, delta=-2.0)
    curr = snap("Running", split_index=0, delta=-2.0)
    names = event_names(detect_events(prev, curr, cfg))
    assert PACE_AHEAD in names


def test_pace_behind(cfg):
    prev = snap("Running", split_index=0, delta=2.0)
    curr = snap("Running", split_index=0, delta=2.0)
    names = event_names(detect_events(prev, curr, cfg))
    assert PACE_BEHIND in names


def test_pace_neutral(cfg):
    prev = snap("Running", split_index=0, delta=0.0)
    curr = snap("Running", split_index=0, delta=0.0)
    names = event_names(detect_events(prev, curr, cfg))
    assert PACE_NEUTRAL in names


# --- split_good when delta is None (no PB data) ---

def test_split_good_when_no_delta(cfg):
    """delta データがなくてもスプリット時は split_good が出る。"""
    prev = snap("Running", split_index=0, delta=None)
    curr = snap("Running", split_index=1, delta=None)
    names = event_names(detect_events(prev, curr, cfg))
    assert SPLIT_CHANGED in names
    assert SPLIT_GOOD in names


# --- split_undo ---

def test_split_undo(cfg):
    prev = snap("Running", split_index=2, delta=None)
    curr = snap("Running", split_index=1, delta=None)
    names = event_names(detect_events(prev, curr, cfg))
    assert SPLIT_UNDO in names
    assert SPLIT_CHANGED not in names


# --- 初回は None ---

def test_no_events_on_first_poll(cfg):
    curr = snap("Running", split_index=0)
    events = detect_events(None, curr, cfg)
    assert events == []
