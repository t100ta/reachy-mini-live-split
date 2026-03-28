from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


class SessionLog:
    """セッション開始/終了サマリをログに記録する。"""

    def __init__(self) -> None:
        self._start_time: float | None = None
        self._event_count = 0
        self._motion_count = 0

    def start(self) -> None:
        self._start_time = time.time()
        logger.info(
            "=== セッション開始 (%s) ===",
            time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(self._start_time)),
        )

    def record_event(self) -> None:
        self._event_count += 1

    def record_motion(self) -> None:
        self._motion_count += 1

    def finish(self) -> None:
        end_time = time.time()
        duration = end_time - (self._start_time or end_time)
        logger.info(
            "=== セッション終了: 経過 %.0f 秒、イベント %d 件、モーション %d 件 ===",
            duration,
            self._event_count,
            self._motion_count,
        )
