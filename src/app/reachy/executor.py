from __future__ import annotations

from abc import ABC, abstractmethod

from app.motions.catalog import MotionDef


class BaseExecutor(ABC):
    """Reachy Mini へのモーション送信を抽象化するインターフェース。"""

    @abstractmethod
    def execute(self, motion: MotionDef) -> None:
        """指定されたモーションを実行する。"""

    @abstractmethod
    def safe_pose(self) -> None:
        """安全ポーズに移行する（シャットダウン時・エラー時に呼ぶ）。"""

    @abstractmethod
    def connect(self) -> None:
        """Reachy に接続する（dry_run の場合は no-op）。"""

    @abstractmethod
    def disconnect(self) -> None:
        """Reachy から切断する。"""
