from __future__ import annotations

import logging
import time

from app.clock import now
from app.config import AppConfig
from app.domain.event_detector import detect_events
from app.domain.state_machine import RuntimeState, set_disconnected, transition
from app.livesplit.poller import poll_once
from app.livesplit.snapshot import LiveSplitSnapshot
from app.motions.cooldown import CooldownTracker
from app.motions.planner import select_motion
from app.reachy.executor import BaseExecutor
from app.telemetry.event_log import EventLog
from app.telemetry.session_log import SessionLog
from app.transports.base import Transport
from app.types import HighLevelState

logger = logging.getLogger(__name__)


def run(
    transport: Transport,
    executor: BaseExecutor,
    cfg: AppConfig,
    event_log: EventLog | None = None,
) -> None:
    """
    メインループ。KeyboardInterrupt または致命的例外が発生するまで実行し続ける。
    """
    poll_interval = cfg.livesplit.poll_interval_ms / 1000.0
    session = SessionLog()
    cooldown = CooldownTracker(
        pose_cooldown_ms=cfg.thresholds.motion_cooldown_ms,
        impulse_cooldown_ms=cfg.thresholds.impulse_cooldown_ms,
    )
    state = RuntimeState()
    prev_snapshot: LiveSplitSnapshot | None = None

    session.start()
    executor.connect()

    try:
        while True:
            loop_start = now()

            # --- ポーリング ---
            snapshot: LiveSplitSnapshot | None = None
            try:
                if not transport.is_connected:
                    logger.info("LiveSplit への接続を試みています...")
                    transport.connect()
                snapshot = poll_once(transport, cfg)
            except ConnectionError as exc:
                logger.warning("LiveSplit 接続エラー: %s", exc)
                transport.close()
                set_disconnected(state)
                _maybe_execute(executor, "disconnected_pose", cooldown, cfg, state, event_log, session)
                _sleep_remaining(loop_start, poll_interval)
                continue

            # --- イベント検出 ---
            events = detect_events(prev_snapshot, snapshot, cfg)

            # --- 状態遷移 ---
            transition(state, events, snapshot, cfg)

            # --- ログ ---
            for event in events:
                logger.debug("Event: %s payload=%s", event.name, event.payload)
                if event_log:
                    event_log.log_event(event)
                session.record_event()

            # --- モーション選択・実行 ---
            t = now()
            motion = select_motion(state, events, cooldown, cfg, t)
            if motion is not None:
                cooldown.record(motion.name, t)
                executor.execute(motion)
                session.record_motion()

                delta = snapshot.delta if snapshot else None
                print(f"[State] {state.state.value}")
                if delta is not None:
                    sign = "-" if delta < 0 else "+"
                    abs_d = abs(delta)
                    mins = int(abs_d // 60)
                    secs = abs_d % 60
                    print(f"[Delta] {sign}{mins:02d}:{secs:05.2f}")

                if event_log and motion:
                    event_log.log_motion(
                        motion,
                        state.state.value,
                        snapshot.delta if snapshot else None,
                    )

            prev_snapshot = snapshot
            _sleep_remaining(loop_start, poll_interval)

    except KeyboardInterrupt:
        logger.info("Ctrl+C を受信しました。終了します。")
    except Exception as exc:
        logger.exception("予期しない例外が発生しました: %s", exc)
    finally:
        try:
            executor.safe_pose()
        except Exception:
            pass
        try:
            transport.close()
        except Exception:
            pass
        if event_log:
            event_log.close()
        session.finish()


def _maybe_execute(executor, motion_name, cooldown, cfg, state, event_log, session):
    """disconnected_pose などを条件付きで実行する。"""
    from app.motions.catalog import CATALOG

    motion = CATALOG.get(motion_name)
    if motion and cooldown.can_execute(motion_name):
        t = now()
        cooldown.record(motion_name, t)
        executor.execute(motion)
        session.record_motion()
        if event_log:
            event_log.log_motion(motion, state.state.value, None)


def _sleep_remaining(loop_start: float, interval: float) -> None:
    elapsed = now() - loop_start
    remaining = interval - elapsed
    if remaining > 0:
        time.sleep(remaining)
