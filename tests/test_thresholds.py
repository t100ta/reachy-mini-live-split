import pytest
from app.config import ThresholdsConfig
from app.domain.thresholds import classify_pace
from app.types import PaceBucket


@pytest.fixture
def cfg():
    return ThresholdsConfig(ahead_seconds=-1.5, behind_seconds=1.5)


def test_ahead(cfg):
    assert classify_pace(-2.0, cfg) == PaceBucket.AHEAD


def test_ahead_boundary(cfg):
    assert classify_pace(-1.5, cfg) == PaceBucket.AHEAD


def test_neutral(cfg):
    assert classify_pace(0.0, cfg) == PaceBucket.NEUTRAL
    assert classify_pace(-1.0, cfg) == PaceBucket.NEUTRAL
    assert classify_pace(1.0, cfg) == PaceBucket.NEUTRAL


def test_behind(cfg):
    assert classify_pace(2.0, cfg) == PaceBucket.BEHIND


def test_behind_boundary(cfg):
    assert classify_pace(1.5, cfg) == PaceBucket.BEHIND


def test_none_is_neutral(cfg):
    assert classify_pace(None, cfg) == PaceBucket.NEUTRAL
