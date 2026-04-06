from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LiveSplitSnapshot:
    """LiveSplit から取得した状態のスナップショット。"""

    captured_at: float
    """取得時刻（monotonic 秒）。"""

    timer_phase: str
    """タイマーフェーズ: "NotRunning" | "Running" | "Paused" | "Ended"。"""

    split_index: int
    """現在のスプリットインデックス（-1 = 未スタート）。"""

    current_split_name: str | None
    """現在のスプリット名（取得できない場合は None）。"""

    current_time: str | None
    """現在のタイム文字列（例: "0:01:23.45"）。"""

    delta: float | None
    """比較タイムとの差（秒）。負 = アヘッド。None = データなし。"""

    attempt_count: int
    """試行回数。"""

    game_name: str | None = None
    """ゲーム名（LiveSplit で設定されている場合）。"""

    category_name: str | None = None
    """カテゴリ名（例: "Any%"）。"""
