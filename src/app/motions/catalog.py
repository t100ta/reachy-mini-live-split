from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MotionDef:
    """モーション定義。"""

    name: str
    """モーション識別名。"""

    is_impulse: bool
    """True = 瞬間反応モーション、False = 継続ポーズ。"""

    duration_ms: int
    """推定所要時間（ミリ秒）。0 = 継続ポーズ。"""

    description: str = ""


# モーションカタログ（10 種）
CATALOG: dict[str, MotionDef] = {
    "idle_pose": MotionDef(
        name="idle_pose",
        is_impulse=False,
        duration_ms=0,
        description="待機ポーズ。最小限の動き。",
    ),
    "ready_pose": MotionDef(
        name="ready_pose",
        is_impulse=True,
        duration_ms=1200,
        description="スタート直後の集中ポーズ。前傾気味。",
    ),
    "running_neutral_pose": MotionDef(
        name="running_neutral_pose",
        is_impulse=False,
        duration_ms=0,
        description="通常走行ポーズ。落ち着いた様子。",
    ),
    "running_ahead_pose": MotionDef(
        name="running_ahead_pose",
        is_impulse=False,
        duration_ms=0,
        description="PB ペース以上のポーズ。前向きで明るい雰囲気。",
    ),
    "running_behind_pose": MotionDef(
        name="running_behind_pose",
        is_impulse=False,
        duration_ms=0,
        description="遅れているポーズ。慎重な様子。",
    ),
    "split_good_nod": MotionDef(
        name="split_good_nod",
        is_impulse=True,
        duration_ms=900,
        description="良いスプリットへの頷き反応。",
    ),
    "split_bad_droop": MotionDef(
        name="split_bad_droop",
        is_impulse=True,
        duration_ms=1000,
        description="悪いスプリットへの一時的な落胆。",
    ),
    "reset_sigh": MotionDef(
        name="reset_sigh",
        is_impulse=True,
        duration_ms=1200,
        description="リセット時のため息。",
    ),
    "finish_celebrate": MotionDef(
        name="finish_celebrate",
        is_impulse=True,
        duration_ms=2500,
        description="フィニッシュ時の喜び。",
    ),
    "disconnected_pose": MotionDef(
        name="disconnected_pose",
        is_impulse=False,
        duration_ms=0,
        description="接続断時のポーズ。控えめ、ほぼ idle 同様。",
    ),
    "talking_pose": MotionDef(
        name="talking_pose",
        is_impulse=True,
        duration_ms=700,
        description="TTS 再生中の話し中モーション。アンテナ交互動作で口パクを表現。",
    ),
    "idle_look": MotionDef(
        name="idle_look",
        is_impulse=True,
        duration_ms=1900,
        description="attentive1: 注目している様子。",
    ),
    "idle_nod": MotionDef(
        name="idle_nod",
        is_impulse=True,
        duration_ms=1200,
        description="attentive2: うなずいて注目。",
    ),
    "idle_curious": MotionDef(
        name="idle_curious",
        is_impulse=True,
        duration_ms=2000,
        description="calming1: 落ち着いて観察している。",
    ),
    "idle_bored": MotionDef(
        name="idle_bored",
        is_impulse=True,
        duration_ms=2500,
        description="boredom1: 少し退屈そう。",
    ),
    "idle_cheerful": MotionDef(
        name="idle_cheerful",
        is_impulse=True,
        duration_ms=1800,
        description="cheerful1: 元気よく待機。",
    ),
    "idle_amazed": MotionDef(
        name="idle_amazed",
        is_impulse=True,
        duration_ms=2200,
        description="amazed1: 驚いた様子。",
    ),
}

# 待機中にランダム再生するアイドルバリエーションモーションの一覧
IDLE_VARIATIONS: list[MotionDef] = [
    CATALOG["idle_look"],
    CATALOG["idle_nod"],
    CATALOG["idle_curious"],
    CATALOG["idle_bored"],
    CATALOG["idle_cheerful"],
    CATALOG["idle_amazed"],
]


def get_motion(name: str) -> MotionDef | None:
    return CATALOG.get(name)
