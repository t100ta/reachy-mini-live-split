from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import reachy_mini  # noqa: F401  — 未インストール時に ImportError を早期発生させる

from app.motions.ambient import HeadTarget
from app.motions.catalog import MotionDef
from app.reachy.executor import BaseExecutor

if TYPE_CHECKING:
    from reachy_mini.motion.recorded_move import RecordedMoves  # type: ignore[import]

logger = logging.getLogger(__name__)

# モーション名 → emotions ライブラリのエントリ名
_EXPRESSION_MAP: dict[str, str] = {
    # メインモーション
    "ready_pose": "enthusiastic1",
    "split_good_nod": "success1",
    "split_bad_droop": "displeased1",
    "reset_sigh": "frustrated1",
    "finish_celebrate": "success2",
    # アイドルバリエーション
    "idle_look": "attentive1",
    "idle_nod": "attentive2",
    "idle_curious": "calming1",
    "idle_bored": "boredom1",
    "idle_cheerful": "cheerful1",
    "idle_amazed": "amazed1",
}


class ReachyExecutor(BaseExecutor):
    """Reachy Mini SDK を使って実際のモーションを送信するエグゼキュータ。"""

    def __init__(self, host: str = "reachy-mini.local") -> None:
        self._host = host
        self._robot = None
        self._emotions: RecordedMoves | None = None

    def connect(self) -> None:
        from reachy_mini import ReachyMini  # type: ignore[import]
        from reachy_mini.motion.recorded_move import RecordedMoves  # type: ignore[import]

        logger.info("Reachy Mini に接続しています: %s", self._host)
        self._robot = ReachyMini(host=self._host, media_backend="no_media")
        self._robot.wake_up()

        logger.info("emotions ライブラリを読み込んでいます（初回はダウンロードあり）")
        self._emotions = RecordedMoves("pollen-robotics/reachy-mini-emotions-library")
        logger.info("Reachy Mini に接続しました")

    def disconnect(self) -> None:
        if self._robot is not None:
            try:
                self._robot.goto_sleep()
                self._robot.__exit__(None, None, None)
            except Exception as exc:
                logger.warning("Reachy 切断時エラー: %s", exc)
            self._robot = None
            logger.info("Reachy Mini との接続を閉じました")

    def safe_pose(self) -> None:
        if self._robot is None:
            return
        try:
            from reachy_mini.utils import create_head_pose  # type: ignore[import]

            logger.info("Reachy: safe_pose に移行します")
            self._robot.goto_target(
                head=create_head_pose(pitch=0, roll=0, yaw=0, degrees=True),
                antennas=[0.2, 0.2],
                duration=1.0,
            )
        except Exception as exc:
            logger.error("safe_pose の実行に失敗しました: %s", exc)

    def goto_ambient(self, target: HeadTarget) -> None:
        if self._robot is None:
            return
        try:
            _goto(
                self._robot,
                pitch=target.pitch,
                roll=target.roll,
                yaw=target.yaw,
                antennas=[target.antenna_l, target.antenna_r],
                duration=target.duration,
            )
        except Exception as exc:
            logger.warning("goto_ambient 失敗: %s", exc)

    def execute(
        self,
        motion: MotionDef,
        sound_cb: Callable[[Path], None] | None = None,
    ) -> None:
        if self._robot is None:
            logger.error("Reachy に接続されていません")
            return
        try:
            logger.info("Reachy: motion=%s", motion.name)
            _dispatch(self._robot, self._emotions, motion, sound_cb)
        except Exception as exc:
            logger.error("モーション %s の実行に失敗しました: %s", motion.name, exc)


def _dispatch(
    robot,
    emotions: RecordedMoves | None,
    motion: MotionDef,
    sound_cb: Callable[[Path], None] | None = None,
) -> None:
    name = motion.name

    # Expression マップにあるモーション: emotions ライブラリを使用
    if name in _EXPRESSION_MAP and emotions is not None:
        expr_name = _EXPRESSION_MAP[name]
        try:
            move = emotions.get(expr_name)
            # 音声コールバック: play_move の前に呼んでブラウザ再生を先行開始
            if sound_cb is not None and move.sound_path is not None:
                sound_cb(move.sound_path)
            robot.play_move(move, sound=False)
            return
        except Exception as exc:
            logger.warning("Expression %s の再生に失敗、フォールバックします: %s", expr_name, exc)

    # 継続ポーズ系（または Expression フォールバック）
    if name == "idle_pose":
        _goto(robot, pitch=0, antennas=[0.2, 0.2], duration=0.4)
    elif name == "running_neutral_pose":
        _goto(robot, pitch=0, antennas=[0.3, 0.3], duration=0.4)
    elif name == "running_ahead_pose":
        _goto(robot, pitch=-10, antennas=[0.7, 0.7], duration=0.4)
    elif name == "running_behind_pose":
        _goto(robot, pitch=12, antennas=[0.05, 0.05], duration=0.4)
    elif name == "disconnected_pose":
        _goto(robot, pitch=5, antennas=[0.0, 0.0], duration=0.4)
    elif name == "ready_pose":
        _goto(robot, pitch=-8, antennas=[0.5, 0.5], duration=0.5)
        _goto(robot, pitch=0, antennas=[0.3, 0.3], duration=0.5)
    elif name == "split_good_nod":
        _goto(robot, pitch=18, antennas=[0.5, 0.5], duration=0.2)
        _goto(robot, pitch=-5, antennas=[0.8, 0.8], duration=0.2)
        _goto(robot, pitch=0, antennas=[0.4, 0.4], duration=0.3)
    elif name == "split_bad_droop":
        _goto(robot, pitch=20, antennas=[0.05, 0.05], duration=0.4)
        _goto(robot, pitch=0, antennas=[0.3, 0.3], duration=0.5)
    elif name == "reset_sigh":
        _goto(robot, pitch=18, antennas=[0.0, 0.0], duration=0.6)
        _goto(robot, pitch=0, antennas=[0.2, 0.2], duration=0.5)
    elif name == "finish_celebrate":
        _goto(robot, yaw=30, antennas=[0.9, 0.9], duration=0.3)
        _goto(robot, yaw=-30, antennas=[0.9, 0.9], duration=0.3)
        _goto(robot, yaw=30, antennas=[0.9, 0.9], duration=0.3)
        _goto(robot, yaw=-30, antennas=[0.9, 0.9], duration=0.3)
        _goto(robot, yaw=0, pitch=-8, antennas=[0.6, 0.6], duration=0.3)
        _goto(robot, pitch=0, antennas=[0.3, 0.3], duration=0.3)
    elif name == "talking_pose":
        _goto(robot, pitch=-5, antennas=[0.7, 0.3], duration=0.15)
        _goto(robot, pitch=-3, antennas=[0.3, 0.7], duration=0.15)
        _goto(robot, pitch=-5, antennas=[0.7, 0.3], duration=0.15)
        _goto(robot, pitch=-3, antennas=[0.3, 0.7], duration=0.15)
        _goto(robot, pitch=0,  antennas=[0.5, 0.5], duration=0.15)
    else:
        logger.warning("未定義のモーション: %s", name)


def _goto(
    robot,
    pitch: float = 0,
    roll: float = 0,
    yaw: float = 0,
    antennas: list[float] | None = None,
    body_yaw: float = 0,
    duration: float = 0.4,
) -> None:
    from reachy_mini.utils import create_head_pose  # type: ignore[import]

    if antennas is None:
        antennas = [0.2, 0.2]
    robot.goto_target(
        head=create_head_pose(pitch=pitch, roll=roll, yaw=yaw, degrees=True),
        antennas=antennas,
        body_yaw=body_yaw,
        duration=duration,
    )
