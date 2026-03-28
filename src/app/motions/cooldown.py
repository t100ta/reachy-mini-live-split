from __future__ import annotations

from app.clock import now as _now


class CooldownTracker:
    """モーションクールダウンを管理する。

    インパルス系（split反応等）と継続ポーズ系で異なるクールダウンを適用する。
    - impulse_cooldown_ms: 瞬間反応モーション用（短め）
    - pose_cooldown_ms: 継続ポーズ用（長め）
    """

    def __init__(
        self,
        pose_cooldown_ms: int = 2000,
        impulse_cooldown_ms: int = 500,
    ) -> None:
        self._pose_cooldown_s = pose_cooldown_ms / 1000.0
        self._impulse_cooldown_s = impulse_cooldown_ms / 1000.0
        self._last_executed: dict[str, float] = {}

    def can_execute(
        self, motion_name: str, is_impulse: bool = False, t: float | None = None
    ) -> bool:
        """クールダウン中でなければ True を返す。"""
        if t is None:
            t = _now()
        last = self._last_executed.get(motion_name)
        if last is None:
            return True
        cooldown = self._impulse_cooldown_s if is_impulse else self._pose_cooldown_s
        return (t - last) >= cooldown

    def record(self, motion_name: str, t: float | None = None) -> None:
        """モーション実行を記録する。"""
        if t is None:
            t = _now()
        self._last_executed[motion_name] = t
