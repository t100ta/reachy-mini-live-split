"""
エントリポイント。

使用例:
    python -m app.main --dry-run
    python -m app.main --config config/app.toml
"""
from __future__ import annotations

import logging
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

    logger.info(
        "起動: host=%s port=%d dry_run=%s",
        cfg.livesplit.host,
        cfg.livesplit.port,
        cfg.reachy.dry_run,
    )

    run(transport, executor, cfg, event_log)
    return 0


if __name__ == "__main__":
    sys.exit(main())
