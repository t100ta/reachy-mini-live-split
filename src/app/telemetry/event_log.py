from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from app.domain.events import InternalEvent
from app.motions.catalog import MotionDef

logger = logging.getLogger(__name__)


class EventLog:
    """内部イベントとモーションを JSONL 形式で保存するロガー。"""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self._path, "a", encoding="utf-8")  # noqa: SIM115

    def log_event(self, event: InternalEvent) -> None:
        record = {
            "type": "event",
            "wall_time": time.time(),
            "name": event.name,
            "at": event.at,
            "payload": event.payload,
        }
        self._write(record)

    def log_motion(self, motion: MotionDef, state_name: str, delta: float | None) -> None:
        record = {
            "type": "motion",
            "wall_time": time.time(),
            "motion": motion.name,
            "state": state_name,
            "delta": delta,
        }
        self._write(record)

    def _write(self, record: dict) -> None:
        try:
            self._file.write(json.dumps(record, ensure_ascii=False) + "\n")
            self._file.flush()
        except OSError as exc:
            logger.warning("イベントログ書き込みエラー: %s", exc)

    def close(self) -> None:
        try:
            self._file.close()
        except OSError:
            pass
