from __future__ import annotations

import logging

from app.clock import now
from app.config import AppConfig
from app.livesplit import commands
from app.livesplit.parser import parse_delta, parse_int, parse_optional_str
from app.livesplit.snapshot import LiveSplitSnapshot
from app.transports.base import Transport

logger = logging.getLogger(__name__)


def poll_once(transport: Transport, cfg: AppConfig) -> LiveSplitSnapshot:
    """
    LiveSplit から 1 回分の状態を取得して LiveSplitSnapshot を返す。
    接続エラー時は ConnectionError を送出する。
    """

    def query(cmd: str) -> str:
        transport.send(cmd)
        return transport.recv_line()

    timer_phase = query(commands.GET_CURRENT_TIMER_PHASE)
    split_index_raw = query(commands.GET_SPLIT_INDEX)
    split_name_raw = query(commands.GET_CURRENT_SPLIT_NAME)
    current_time_raw = query(commands.GET_CURRENT_TIME)
    delta_raw = query(commands.get_delta(cfg.livesplit.comparison))
    attempt_raw = query(commands.GET_ATTEMPT_COUNT)

    snapshot = LiveSplitSnapshot(
        captured_at=now(),
        timer_phase=timer_phase.strip(),
        split_index=parse_int(split_index_raw),
        current_split_name=parse_optional_str(split_name_raw),
        current_time=parse_optional_str(current_time_raw),
        delta=parse_delta(delta_raw),
        attempt_count=parse_int(attempt_raw, default=0),
    )
    logger.debug(
        "Snapshot: phase=%s idx=%d delta=%s",
        snapshot.timer_phase,
        snapshot.split_index,
        snapshot.delta,
    )
    return snapshot
