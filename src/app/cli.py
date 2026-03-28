from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass
class CliArgs:
    dry_run: bool
    config: str | None
    log_level: str
    host: str | None
    port: int | None
    transport: str | None


def parse_args(argv: list[str] | None = None) -> CliArgs:
    parser = argparse.ArgumentParser(
        prog="python -m app.main",
        description="Reachy Mini × LiveSplit 連携アプリ",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Reachy に接続せず、モーションをログ出力のみにする",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        help="設定ファイルのパス（TOML）",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="ログレベル（デフォルト: INFO）",
    )
    parser.add_argument(
        "--host",
        help="LiveSplit サーバーのホスト（設定ファイルを上書き）",
    )
    parser.add_argument(
        "--port",
        type=int,
        help="LiveSplit サーバーのポート（設定ファイルを上書き）",
    )
    parser.add_argument(
        "--transport",
        choices=["tcp", "ws"],
        help="トランスポートの種別（デフォルト: tcp）",
    )

    ns = parser.parse_args(argv)
    return CliArgs(
        dry_run=ns.dry_run,
        config=ns.config,
        log_level=ns.log_level,
        host=ns.host,
        port=ns.port,
        transport=ns.transport,
    )
