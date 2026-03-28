from __future__ import annotations

import re


def parse_int(raw: str, default: int = -1) -> int:
    """文字列を int に変換する。失敗時は default を返す。"""
    try:
        return int(raw.strip())
    except (ValueError, AttributeError):
        return default


def parse_optional_str(raw: str) -> str | None:
    """空文字列や "-" の場合は None、それ以外はそのまま返す。"""
    stripped = raw.strip()
    if stripped in ("", "-"):
        return None
    return stripped


_TIME_RE = re.compile(
    r"^-?(\d+):(\d{2}):(\d{2})\.(\d+)$"
)


def parse_delta(raw: str) -> float | None:
    """
    LiveSplit の delta レスポンスを秒（float）に変換する。

    形式: "-H:MM:SS.mm" or "H:MM:SS.mm"
    LiveSplit が "-" を返した場合（比較データなし）は None を返す。
    """
    stripped = raw.strip()
    if stripped in ("", "-"):
        return None

    negative = stripped.startswith("-")
    s = stripped.lstrip("-")

    m = _TIME_RE.match("-" + s if not stripped.startswith("-") else stripped.lstrip("-"))
    # 再マッチ: stripped から符号を除いたものに対して適用
    m = _TIME_RE.match(s)
    if not m:
        return None

    hours = int(m.group(1))
    minutes = int(m.group(2))
    seconds = int(m.group(3))
    frac_str = m.group(4)
    frac = int(frac_str) / (10 ** len(frac_str))

    total = hours * 3600 + minutes * 60 + seconds + frac
    return -total if negative else total
