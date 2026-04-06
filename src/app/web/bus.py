from __future__ import annotations

import queue


class EventBus:
    """同期メインループと非同期 WebSocket スレッド間のブリッジ。"""

    def __init__(self) -> None:
        self._q: queue.Queue[dict] = queue.Queue()

    def post(self, msg: dict) -> None:
        self._q.put_nowait(msg)

    def drain(self) -> list[dict]:
        msgs: list[dict] = []
        while True:
            try:
                msgs.append(self._q.get_nowait())
            except queue.Empty:
                break
        return msgs
