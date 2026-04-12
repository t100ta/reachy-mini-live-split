from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

_ENV_VAR_RE = re.compile(r"^\$\{(\w+)\}$")


def _expand(value: object) -> object:
    """文字列値の `${VAR}` を環境変数に展開する。"""
    if not isinstance(value, str):
        return value
    m = _ENV_VAR_RE.match(value)
    if m:
        return os.environ.get(m.group(1), "")
    return value


def _expand_dict(d: dict) -> dict:
    return {k: _expand(v) for k, v in d.items()}


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
    idle_variation_interval_ms: int = 45_000
    expression_sound_volume: float = 0.35


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
class WebConfig:
    enabled: bool = False
    host: str = "0.0.0.0"
    port: int = 8765
    audio_path: str = "logs/audio"


@dataclass
class TtsConfig:
    enabled: bool = False
    engine: str = "openai"            # "openai" | "coeiroink"
    openai_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    tts_model: str = "tts-1"
    tts_voice: str = "alloy"
    coeiroink_url: str = "http://127.0.0.1:50032"
    coeiroink_speaker_name: str = ""
    coeiroink_style_name: str = ""
    igdb_client_id: str = ""
    igdb_client_secret: str = ""
    game_cache_path: str = "logs/game_cache.json"
    game_name: str = ""      # LiveSplit から取得できない場合の手動設定
    category_name: str = ""  # 同上
    comment_events: list[str] = field(default_factory=lambda: [
        "run_started", "split_good", "split_bad", "run_finished", "run_reset"
    ])
    audio_path: str = "logs/audio"


@dataclass
class AmbientConfig:
    enabled: bool = True
    strength: float = 1.0           # グローバル強度倍率 (0.0–1.0)
    update_duration: float = 0.4    # goto_target に渡す duration (秒)
    # idle_breathing
    breathing_amplitude: float = 2.5    # ピッチ最大振れ幅 (degree)
    breathing_period: float = 4.0       # 1周期の秒数
    # curiosity_glance
    glance_interval_min: float = 30.0   # グランス間隔の最小秒数
    glance_interval_max: float = 60.0   # グランス間隔の最大秒数
    glance_amplitude: float = 5.0       # ヨー最大振れ幅 (degree)
    glance_return_duration: float = 1.2 # グランス1回分の合計秒数
    # running_sway: RUNNING 中の緩やかな pitch 揺れ（idle_breathing より小さく遅い）
    running_sway_amplitude: float = 1.5  # degree
    running_sway_period: float = 6.0     # 秒
    # thinking_tilt
    tilt_amplitude: float = 3.0          # ロール最大振れ幅 (degree)
    tilt_period: float = 8.0             # 1周期の秒数
    # afterglow / sag
    afterglow_duration: float = 3.0      # SPLIT_GOOD 後のアフターグロー秒数
    sag_duration: float = 2.0            # SPLIT_BAD 後のサグ秒数
    # インパルスモーション後にアンビエントを一時停止する秒数
    post_impulse_pause: float = 0.8


@dataclass
class AppConfig:
    livesplit: LiveSplitConfig = field(default_factory=LiveSplitConfig)
    thresholds: ThresholdsConfig = field(default_factory=ThresholdsConfig)
    reachy: ReachyConfig = field(default_factory=ReachyConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    motions: dict[str, MotionEntry] = field(default_factory=dict)
    web: WebConfig = field(default_factory=WebConfig)
    tts: TtsConfig = field(default_factory=TtsConfig)
    ambient: AmbientConfig = field(default_factory=AmbientConfig)


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
        cfg.livesplit = LiveSplitConfig(**{k: v for k, v in _expand_dict(ls).items() if k in LiveSplitConfig.__dataclass_fields__})

    if th := data.get("thresholds"):
        cfg.thresholds = ThresholdsConfig(**{k: v for k, v in _expand_dict(th).items() if k in ThresholdsConfig.__dataclass_fields__})

    if rc := data.get("reachy"):
        cfg.reachy = ReachyConfig(**{k: v for k, v in _expand_dict(rc).items() if k in ReachyConfig.__dataclass_fields__})

    if lg := data.get("logging"):
        cfg.logging = LoggingConfig(**{k: v for k, v in _expand_dict(lg).items() if k in LoggingConfig.__dataclass_fields__})

    if motions := data.get("motions"):
        for name, vals in motions.items():
            cfg.motions[name] = MotionEntry(**{k: v for k, v in _expand_dict(vals).items() if k in MotionEntry.__dataclass_fields__})

    if web := data.get("web"):
        cfg.web = WebConfig(**{k: v for k, v in _expand_dict(web).items() if k in WebConfig.__dataclass_fields__})

    if tts := data.get("tts"):
        cfg.tts = TtsConfig(**{k: v for k, v in _expand_dict(tts).items() if k in TtsConfig.__dataclass_fields__})

    if ambient := data.get("ambient"):
        cfg.ambient = AmbientConfig(**{k: v for k, v in _expand_dict(ambient).items() if k in AmbientConfig.__dataclass_fields__})

    return cfg
