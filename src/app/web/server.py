from __future__ import annotations

import asyncio
import json
import logging
import queue as _queue
import threading
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse

from app.config import WebConfig
from app.web.bus import EventBus

logger = logging.getLogger(__name__)

_HTML_PATH = Path(__file__).parent / "console.html"


class ConnectionManager:
    """接続中の WebSocket クライアントを管理し broadcast を提供する。"""

    def __init__(self) -> None:
        self._clients: list[WebSocket] = []
        self._lock = asyncio.Lock()
        self.audio_done_event = asyncio.Event()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.append(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients = [c for c in self._clients if c is not ws]

    async def broadcast(self, msg: dict) -> None:
        data = json.dumps(msg, ensure_ascii=False)
        dead: list[WebSocket] = []
        async with self._lock:
            clients = list(self._clients)
        for ws in clients:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)

    def notify_audio_done(self) -> None:
        self.audio_done_event.set()
        self.audio_done_event.clear()


def create_app(cfg: WebConfig, bus: EventBus, audio_done_queue: _queue.SimpleQueue | None = None) -> FastAPI:
    app = FastAPI()
    manager = ConnectionManager()

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        return HTMLResponse(_HTML_PATH.read_text(encoding="utf-8"))

    @app.get("/audio/{filename}")
    async def audio(filename: str) -> FileResponse:
        path = Path(cfg.audio_path) / filename
        media_type = "audio/wav" if filename.endswith(".wav") else "audio/mpeg"
        return FileResponse(str(path), media_type=media_type)

    @app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket) -> None:
        await manager.connect(websocket)
        logger.info("WebSocket クライアントが接続しました")
        try:
            while True:
                text = await websocket.receive_text()
                try:
                    msg = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if msg.get("type") == "audio_done":
                    if audio_done_queue is not None:
                        audio_done_queue.put_nowait(True)
                    else:
                        bus.post({"type": "audio_done"})
        except WebSocketDisconnect:
            pass
        finally:
            await manager.disconnect(websocket)
            logger.info("WebSocket クライアントが切断しました")

    # バックグラウンドタスク: EventBus をポーリングして broadcast
    @app.on_event("startup")
    async def _start_broadcaster() -> None:
        asyncio.create_task(_broadcast_loop(bus, manager))

    return app


async def _broadcast_loop(bus: EventBus, manager: ConnectionManager) -> None:
    while True:
        msgs = bus.drain()
        for msg in msgs:
            await manager.broadcast(msg)
        await asyncio.sleep(0.05)


def start_server(cfg: WebConfig, bus: EventBus, audio_done_queue: _queue.SimpleQueue | None = None) -> threading.Thread:
    """uvicorn を daemon thread で起動して Thread を返す。"""
    app = create_app(cfg, bus, audio_done_queue)
    config = uvicorn.Config(
        app,
        host=cfg.host,
        port=cfg.port,
        log_level="warning",
        loop="asyncio",
    )
    server = uvicorn.Server(config)

    def _run() -> None:
        asyncio.run(server.serve())

    thread = threading.Thread(target=_run, daemon=True, name="web-server")
    thread.start()
    logger.info("Web コンソールを起動しました: http://%s:%d", cfg.host, cfg.port)
    return thread
