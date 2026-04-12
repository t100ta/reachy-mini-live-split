from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from app.motions.catalog import MotionDef
from app.reachy.executor import BaseExecutor

if TYPE_CHECKING:
    from app.motions.ambient import HeadTarget

logger = logging.getLogger(__name__)


class DryExecutor(BaseExecutor):
    """ドライラン用エグゼキュータ。実際には何も動かさずログ出力のみ行う。"""

    def connect(self) -> None:
        logger.info("[DryRun] Reachy 接続をスキップ（dry-run モード）")

    def disconnect(self) -> None:
        logger.info("[DryRun] Reachy 切断をスキップ（dry-run モード）")

    def execute(
        self,
        motion: MotionDef,
        sound_cb: Callable[[Path], None] | None = None,
    ) -> None:
        print(f"[Motion] {motion.name}")
        logger.info("[DryRun] Motion: %s", motion.name)

    def goto_ambient(self, target: HeadTarget) -> None:
        logger.debug(
            "[DryRun] goto_ambient pitch=%.1f roll=%.1f yaw=%.1f ant=[%.2f, %.2f]",
            target.pitch, target.roll, target.yaw, target.antenna_l, target.antenna_r,
        )

    def safe_pose(self) -> None:
        print("[Motion] safe_pose")
        logger.info("[DryRun] safe_pose")
