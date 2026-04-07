from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable

from app.motions.catalog import MotionDef


class BaseExecutor(ABC):
    """Reachy Mini へのモーション送信を抽象化するインターフェース。"""

    @abstractmethod
    def execute(
        self,
        motion: MotionDef,
        sound_cb: Callable[[Path], None] | None = None,
    ) -> None:
        """指定されたモーションを実行する。

        sound_cb: Expressions に音声ファイルがある場合に呼ばれるコールバック。
                  引数は WAV ファイルの Path。ブラウザ音声配信に使用する。
        """

    @abstractmethod
    def safe_pose(self) -> None:
        """安全ポーズに移行する（シャットダウン時・エラー時に呼ぶ）。"""

    @abstractmethod
    def connect(self) -> None:
        """Reachy に接続する（dry_run の場合は no-op）。"""

    @abstractmethod
    def disconnect(self) -> None:
        """Reachy から切断する。"""
