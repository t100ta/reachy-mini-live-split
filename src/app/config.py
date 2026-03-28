from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class LiveSplitConfig:
    transport: str = "ws"
    host: str = "127.0.0.1"
    port: int = 16834
    poll_interval_ms: int = 200
    comparison: str = "Personal Best"


@dataclass
class ThresholdsConfig:
    ahead_seconds: float = -1.5
    behind_seconds: float = 1.5
    pace_debounce_ms: int = 1200
    motion_cooldown_ms: int = 2000
    impulse_cooldown_ms: int = 500
    split_priority_ms: int = 1500
    ready_duration_ms: int = 1200
    finished_duration_ms: int = 2500


@dataclass
class ReachyConfig:
    enabled: bool = True
    dry_run: bool = False
    host: str = "reachy-mini.local"


@dataclass
class LoggingConfig:
    level: str = "INFO"
    jsonl_path: str = "logs/session.jsonl"


@dataclass
class MotionEntry:
    enabled: bool = True
    duration_ms: int = 0


@dataclass
class AppConfig:
    livesplit: LiveSplitConfig = field(default_factory=LiveSplitConfig)
    thresholds: ThresholdsConfig = field(default_factory=ThresholdsConfig)
    reachy: ReachyConfig = field(default_factory=ReachyConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    motions: dict[str, MotionEntry] = field(default_factory=dict)


def load_config(path: str | Path | None) -> AppConfig:
    if path is None:
        return AppConfig()

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "rb") as f:
        data = tomllib.load(f)

    cfg = AppConfig()

    if ls := data.get("livesplit"):
        cfg.livesplit = LiveSplitConfig(**{k: v for k, v in ls.items() if hasattr(LiveSplitConfig, k) or k in LiveSplitConfig.__dataclass_fields__})

    if th := data.get("thresholds"):
        cfg.thresholds = ThresholdsConfig(**{k: v for k, v in th.items() if k in ThresholdsConfig.__dataclass_fields__})

    if re := data.get("reachy"):
        cfg.reachy = ReachyConfig(**{k: v for k, v in re.items() if k in ReachyConfig.__dataclass_fields__})

    if lg := data.get("logging"):
        cfg.logging = LoggingConfig(**{k: v for k, v in lg.items() if k in LoggingConfig.__dataclass_fields__})

    if motions := data.get("motions"):
        for name, vals in motions.items():
            cfg.motions[name] = MotionEntry(**{k: v for k, v in vals.items() if k in MotionEntry.__dataclass_fields__})

    return cfg
