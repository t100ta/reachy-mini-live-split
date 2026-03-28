from __future__ import annotations

import logging
import time

import websocket as _ws

from app.transports.base import Transport

logger = logging.getLogger(__name__)

_WS_PATH = "/livesplit"
_TIMEOUT = 5.0


class WsTransport(Transport):
    """LiveSplit WebSocket サーバーへの接続。再接続ロジック付き。"""

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
        self._ws: _ws.WebSocket | None = None

    # ------------------------------------------------------------------
    # Transport interface
    # ------------------------------------------------------------------

    def connect(self) -> None:
        attempt = 0
        url = f"ws://{self._host}:{self._port}{_WS_PATH}"
        while True:
            try:
                sock = _ws.WebSocket()
                sock.connect(url, timeout=_TIMEOUT)
                self._ws = sock
                logger.info("LiveSplit (WS) に接続しました: %s", url)
                return
            except Exception as exc:
                attempt += 1
                if self._max_retries is not None and attempt >= self._max_retries:
                    raise ConnectionError(
                        f"LiveSplit WS への接続に失敗しました（{attempt} 回試行）: {exc}"
                    ) from exc
                logger.warning(
                    "LiveSplit WS 接続失敗（試行 %d）: %s。%s 秒後にリトライします",
                    attempt,
                    exc,
                    self._retry_interval,
                )
                time.sleep(self._retry_interval)

    def send(self, command: str) -> None:
        if self._ws is None:
            raise ConnectionError("接続されていません")
        try:
            self._ws.send(command)
        except Exception as exc:
            self._ws = None
            raise ConnectionError(f"送信エラー: {exc}") from exc

    def recv_line(self) -> str:
        if self._ws is None:
            raise ConnectionError("接続されていません")
        try:
            return self._ws.recv()
        except Exception as exc:
            self._ws = None
            raise ConnectionError(f"受信エラー: {exc}") from exc

    def close(self) -> None:
        if self._ws is not None:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None
            logger.info("LiveSplit (WS) との接続を閉じました")

    @property
    def is_connected(self) -> bool:
        return self._ws is not None
