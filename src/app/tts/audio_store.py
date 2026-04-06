from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioStore:
    """音声ファイル（mp3 / wav）の保存・管理。"""

    def __init__(self, audio_path: str) -> None:
        self._dir = Path(audio_path)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._counter = self._next_index()

    def _next_index(self) -> int:
        existing = sorted(
            p for p in self._dir.iterdir()
            if p.suffix in (".mp3", ".wav") and p.stem.isdigit()
        )
        if not existing:
            return 0
        last = int(existing[-1].stem)
        return last + 1

    def save(self, audio_bytes: bytes, suffix: str = ".mp3") -> str:
        filename = f"{self._counter:04d}{suffix}"
        path = self._dir / filename
        path.write_bytes(audio_bytes)
        self._counter += 1
        self.cleanup_old()
        return filename

    def cleanup_old(self, max_files: int = 30) -> None:
        files = sorted(
            p for p in self._dir.iterdir()
            if p.suffix in (".mp3", ".wav") and p.stem.isdigit()
        )
        for old in files[:-max_files]:
            try:
                old.unlink()
            except OSError as exc:
                logger.warning("音声ファイルの削除に失敗: %s", exc)
