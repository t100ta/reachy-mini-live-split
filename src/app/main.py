"""
エントリポイント。

使用例:
    python -m app.main --dry-run
    python -m app.main --config config/app.toml
"""
from __future__ import annotations

import logging
import queue as _queue
import sys

from app.app import run
from app.cli import parse_args
from app.config import load_config
from app.logging_setup import setup_logging
from app.telemetry.event_log import EventLog
from app.transports.tcp_client import TcpTransport
from app.transports.ws_client import WsTransport

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    # ログ設定（CLI 引数優先）
    setup_logging(args.log_level)

    # 設定ファイル読み込み
    try:
        cfg = load_config(args.config)
    except FileNotFoundError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1

    # CLI 引数で設定を上書き
    if args.dry_run:
        cfg.reachy.dry_run = True
        cfg.reachy.enabled = False
    if args.host:
        cfg.livesplit.host = args.host
    if args.port:
        cfg.livesplit.port = args.port
    if args.transport:
        cfg.livesplit.transport = args.transport

    # トランスポート選択（デフォルト: ws）
    transport_type = cfg.livesplit.transport
    if transport_type == "tcp":
        transport = TcpTransport(
            host=cfg.livesplit.host,
            port=cfg.livesplit.port,
        )
    else:
        transport = WsTransport(
            host=cfg.livesplit.host,
            port=cfg.livesplit.port,
        )

    # エグゼキュータ選択
    if cfg.reachy.dry_run or not cfg.reachy.enabled:
        from app.reachy.dry_executor import DryExecutor

        executor = DryExecutor()
    else:
        try:
            from app.reachy.real_executor import ReachyExecutor  # type: ignore[import]

            executor = ReachyExecutor(host=cfg.reachy.host)
        except ImportError:
            logger.warning(
                "reachy_mini パッケージが見つかりません。dry-run モードで起動します。"
            )
            from app.reachy.dry_executor import DryExecutor

            executor = DryExecutor()

    # イベントログ
    event_log: EventLog | None = None
    if cfg.logging.jsonl_path:
        event_log = EventLog(cfg.logging.jsonl_path)

    # Web コンソール
    event_bus = None
    audio_done_queue: _queue.SimpleQueue | None = None
    if cfg.web.enabled:
        from app.web.bus import EventBus
        from app.web.server import start_server
        event_bus = EventBus()
        audio_done_queue = _queue.SimpleQueue()
        start_server(cfg.web, event_bus, audio_done_queue)

    # TTS サービス
    tts_service = None
    if cfg.tts.enabled:
        try:
            from app.tts.service import TTSService
            tts_service = TTSService(cfg.tts)
        except Exception as exc:
            logger.warning("TTS サービスの初期化に失敗しました（無効化）: %s", exc)

    logger.info(
        "起動: host=%s port=%d dry_run=%s web=%s tts=%s",
        cfg.livesplit.host,
        cfg.livesplit.port,
        cfg.reachy.dry_run,
        cfg.web.enabled,
        cfg.tts.enabled,
    )

    run(transport, executor, cfg, event_log, event_bus, tts_service, audio_done_queue)
    return 0


if __name__ == "__main__":
    sys.exit(main())
