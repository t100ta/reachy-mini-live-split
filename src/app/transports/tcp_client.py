from __future__ import annotations

import logging
import socket
import time

from app.transports.base import Transport

logger = logging.getLogger(__name__)

_RECV_BUFSIZE = 4096
_LINE_TIMEOUT = 5.0  # seconds


class TcpTransport(Transport):
    """LiveSplit サーバーへの TCP 接続。再接続ロジック付き。"""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 16834,
        retry_interval: float = 3.0,
        max_retries: int | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._retry_interval = retry_interval
        self._max_retries = max_retries
        self._sock: socket.socket | None = None
        self._buf: bytes = b""

    # ------------------------------------------------------------------
    # Transport interface
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """TCP 接続を確立する。成功するまで retry_interval 秒ごとにリトライする。"""
        attempt = 0
        while True:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(_LINE_TIMEOUT)
                sock.connect((self._host, self._port))
                self._sock = sock
                self._buf = b""
                logger.info("LiveSplit に接続しました: %s:%d", self._host, self._port)
                return
            except OSError as exc:
                attempt += 1
                if self._max_retries is not None and attempt >= self._max_retries:
                    raise ConnectionError(
                        f"LiveSplit への接続に失敗しました（{attempt} 回試行）: {exc}"
                    ) from exc
                logger.warning(
                    "LiveSplit への接続失敗（試行 %d）: %s。%s 秒後にリトライします",
                    attempt,
                    exc,
                    self._retry_interval,
                )
                time.sleep(self._retry_interval)

    def _close_sock(self) -> None:
        """ソケットを閉じて None にする。"""
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
            self._buf = b""

    def send(self, command: str) -> None:
        if self._sock is None:
            raise ConnectionError("接続されていません")
        data = (command + "\r\n").encode("utf-8")
        try:
            self._sock.sendall(data)
        except OSError as exc:
            self._close_sock()
            raise ConnectionError(f"送信エラー: {exc}") from exc

    def recv_line(self) -> str:
        if self._sock is None:
            raise ConnectionError("接続されていません")
        while b"\r\n" not in self._buf:
            try:
                chunk = self._sock.recv(_RECV_BUFSIZE)
            except OSError as exc:
                self._close_sock()
                raise ConnectionError(f"受信エラー: {exc}") from exc
            if not chunk:
                self._close_sock()
                raise ConnectionError("接続が切断されました")
            self._buf += chunk
        line, self._buf = self._buf.split(b"\r\n", 1)
        return line.decode("utf-8")

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
            logger.info("LiveSplit との接続を閉じました")

    @property
    def is_connected(self) -> bool:
        return self._sock is not None
