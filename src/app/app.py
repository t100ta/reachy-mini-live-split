from __future__ import annotations

import logging
import queue as _queue
import shutil
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

from app.clock import now
from app.config import AppConfig
from app.domain.event_detector import detect_events
from app.domain.state_machine import RuntimeState, set_disconnected, transition
from app.livesplit.poller import fetch_game_info, poll_once
from app.livesplit.snapshot import LiveSplitSnapshot
from app.motions.ambient import AmbientMotionController
from app.motions.catalog import CATALOG
from app.motions.cooldown import CooldownTracker
from app.motions.planner import select_motion
from app.reachy.executor import BaseExecutor
from app.telemetry.event_log import EventLog
from app.telemetry.session_log import SessionLog
from app.transports.base import Transport
from app.types import HighLevelState

if TYPE_CHECKING:
    from app.tts.service import TTSService
    from app.web.bus import EventBus

logger = logging.getLogger(__name__)


def run(
    transport: Transport,
    executor: BaseExecutor,
    cfg: AppConfig,
    event_log: EventLog | None = None,
    event_bus: EventBus | None = None,
    tts_service: TTSService | None = None,
    audio_done_queue: _queue.SimpleQueue | None = None,
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
    tts_future: Future | None = None
    talking_until: float = 0.0
    ambient = AmbientMotionController(cfg.ambient)
    ambient_resume_at: float = 0.0  # インパルス後のアンビエント一時停止終了時刻

    # Expression 音声をブラウザへ配信するコールバック
    _expr_audio_dir = Path(cfg.web.audio_path)

    def _sound_cb(sound_path: Path) -> None:
        """Expression の WAV を logs/audio/ にコピーしてブラウザへ送信する。"""
        if not event_bus:
            return
        if now() < talking_until:
            # TTS 再生中は音声が重なるためスキップ
            return
        dest_name = f"expr_{sound_path.stem}.wav"
        dest = _expr_audio_dir / dest_name
        try:
            if not dest.exists():
                _expr_audio_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy(sound_path, dest)
            event_bus.post({
                "type": "play_audio",
                "url": f"/audio/{dest_name}",
                "volume": cfg.thresholds.expression_sound_volume,
                "notify_done": False,
            })
        except Exception as exc:
            logger.warning("Expression 音声の配信に失敗: %s", exc)
    cached_game_name: str | None = None
    cached_category_name: str | None = None
    game_name_supported: bool | None = None  # None=未確認, True=対応, False=未対応
    tts_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tts") if tts_service else None
    comment_events = set(cfg.tts.comment_events)

    session.start()
    executor.connect()

    try:
        while True:
            loop_start = now()

            # --- TTS 完了チェック ---
            if tts_future is not None and tts_future.done():
                try:
                    filename, duration, tts_text = tts_future.result()
                    talking_until = now() + duration
                    if event_bus:
                        event_bus.post({
                            "type": "play_audio",
                            "url": f"/audio/{filename}",
                            "text": tts_text,
                        })
                except Exception as exc:
                    logger.warning("TTS 失敗: %s", exc)
                tts_future = None

            # --- audio_done 受信チェック ---
            if audio_done_queue:
                while True:
                    try:
                        audio_done_queue.get_nowait()
                        talking_until = 0.0
                    except _queue.Empty:
                        break

            # --- ポーリング ---
            snapshot: LiveSplitSnapshot | None = None
            try:
                if not transport.is_connected:
                    logger.info("LiveSplit への接続を試みています...")
                    transport.connect()
                    # 接続直後にゲーム名・カテゴリを取得（未対応なら以降スキップ）
                    if tts_service and game_name_supported is not False:
                        new_game, new_cat = fetch_game_info(transport)
                        if new_game:
                            game_name_supported = True
                            cached_game_name = new_game
                            cached_category_name = new_cat
                            logger.info("ゲーム: %s / %s", cached_game_name, cached_category_name)
                        elif not transport.is_connected:
                            # コマンド未対応で切断された
                            game_name_supported = False
                            logger.info("getgamename は未対応のため以降スキップします")
                            # config フォールバック
                            if not cached_game_name and cfg.tts.game_name:
                                cached_game_name = cfg.tts.game_name
                            if not cached_category_name and cfg.tts.category_name:
                                cached_category_name = cfg.tts.category_name
                            # サーバーが accept ループを再開する時間を与えるため今回はスキップ
                            _sleep_remaining(loop_start, poll_interval)
                            continue
                        # config フォールバック
                        if not cached_game_name and cfg.tts.game_name:
                            cached_game_name = cfg.tts.game_name
                        if not cached_category_name and cfg.tts.category_name:
                            cached_category_name = cfg.tts.category_name
                        # 切断されていた場合は再接続
                        if not transport.is_connected:
                            transport.connect()
                snapshot = poll_once(transport, cfg)
            except ConnectionError as exc:
                logger.warning("LiveSplit 接続エラー: %s", exc)
                transport.close()
                set_disconnected(state)
                _maybe_execute(executor, "disconnected_pose", cooldown, cfg, state, event_log, session)
                if event_bus:
                    event_bus.post({"type": "state", "state": "disconnected"})
                _sleep_remaining(loop_start, poll_interval)
                continue

            # --- イベント検出 ---
            events = detect_events(prev_snapshot, snapshot, cfg)

            # --- 状態遷移 ---
            transition(state, events, snapshot, cfg)

            # --- ログ・broadcast ---
            for event in events:
                logger.debug("Event: %s payload=%s", event.name, event.payload)
                if event_log:
                    event_log.log_event(event)
                session.record_event()
                if event_bus:
                    event_bus.post({
                        "type": "event",
                        "name": event.name,
                        "split_name": (snapshot.current_split_name if snapshot else None),
                        "delta": (snapshot.delta if snapshot else None),
                    })

            # --- 状態 broadcast ---
            if event_bus and snapshot:
                event_bus.post({
                    "type": "state",
                    "state": state.state.value,
                    "delta": snapshot.delta,
                })

            # --- ゲーム名の動的更新（run_started 時に再取得） ---
            if tts_service and game_name_supported is True and any(e.name == "run_started" for e in events):
                new_game, new_cat = fetch_game_info(transport)
                if new_game and new_game != cached_game_name:
                    logger.info("ゲームが変わりました: %s / %s", new_game, new_cat)
                    cached_game_name = new_game
                    cached_category_name = new_cat
                if not transport.is_connected:
                    transport.connect()

            # --- TTS 起動（コメントイベント発生時） ---
            if tts_service and tts_future is None:
                event_names = {e.name for e in events}
                triggered = event_names & comment_events
                if triggered:
                    event_name = next(iter(triggered))
                    # split_good/split_bad は完了したスプリット名（prev_snapshot）を使う
                    split_name = (
                        prev_snapshot.current_split_name if prev_snapshot else None
                        if event_name in ("split_good", "split_bad")
                        else (snapshot.current_split_name if snapshot else None)
                    )
                    delta = snapshot.delta if snapshot else None
                    tts_future = tts_pool.submit(
                        tts_service.generate,
                        event_name, split_name, delta,
                        cached_game_name,
                        cached_category_name,
                    )

            # --- モーション選択・実行 ---
            t = now()
            if t < talking_until:
                # TTS 再生中: talking_pose をループ実行
                motion = CATALOG.get("talking_pose")
                if motion and cooldown.can_execute("talking_pose", is_impulse=True, t=t):
                    cooldown.record("talking_pose", t)
                    executor.execute(motion)
                    session.record_motion()
            else:
                motion = select_motion(state, events, cooldown, cfg, t)

                if motion is not None and motion.is_impulse:
                    # インパルスモーション（イベントリアクション・アイドルバリエーション）
                    cooldown.record(motion.name, t)
                    executor.execute(motion, _sound_cb)
                    session.record_motion()
                    # インパルス後しばらくアンビエントを止め、モーションの余韻を残す
                    ambient_resume_at = now() + cfg.ambient.post_impulse_pause

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

                elif (
                    cfg.ambient.enabled
                    and t >= ambient_resume_at       # インパルス後の待機期間を過ぎた
                    and t >= state.impulse_until     # スプリット優先ウィンドウ外
                    and state.state not in (HighLevelState.DISCONNECTED, HighLevelState.SAFE_MODE)
                ):
                    # アンビエントモード: 連続的なターゲット姿勢を送信
                    ambient.notify_events(events, t)
                    target = ambient.compute_target(state, t)
                    executor.goto_ambient(target)

                else:
                    # アンビエント無効時: プランナーの継続ポーズをそのまま使う
                    if motion is not None:
                        cooldown.record(motion.name, t)
                        executor.execute(motion, _sound_cb)
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
        if tts_pool:
            tts_pool.shutdown(wait=False)
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
