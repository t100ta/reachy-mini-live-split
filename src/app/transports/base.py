from __future__ import annotations

from abc import ABC, abstractmethod


class Transport(ABC):
    """LiveSplit サーバーへの接続を抽象化するインターフェース。"""

    @abstractmethod
    def connect(self) -> None:
        """接続を確立する。失敗時は例外を送出する。"""

    @abstractmethod
    def send(self, command: str) -> None:
        """コマンド文字列を送信する（\r\n は自動付加）。"""

    @abstractmethod
    def recv_line(self) -> str:
        """1行分のレスポンスを受信して返す（\r\n 除去済み）。"""

    @abstractmethod
    def close(self) -> None:
        """接続を閉じる。"""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """現在接続中かどうか。"""
