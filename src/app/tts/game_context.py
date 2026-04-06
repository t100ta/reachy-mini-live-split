from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class GameContext:
    name: str
    summary: str | None
    storyline: str | None
    fetched_at: str  # ISO8601


class GameContextCache:
    """IGDB からゲーム概要を取得してローカル JSON にキャッシュする。"""

    def __init__(self, cache_path: str) -> None:
        self._path = Path(cache_path)
        self._data: dict[str, dict] = self._load()

    def _load(self) -> dict[str, dict]:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("ゲームキャッシュの読み込みに失敗しました: %s", exc)
        return {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get(self, game_name: str) -> GameContext | None:
        key = game_name.lower()
        entry = self._data.get(key)
        if entry:
            return GameContext(**entry)
        return None

    def fetch_and_cache(
        self,
        game_name: str,
        client_id: str,
        client_secret: str,
    ) -> GameContext | None:
        """IGDB からゲーム情報を取得してキャッシュに保存する。"""
        try:
            import httpx
        except ImportError:
            logger.warning("httpx が見つかりません。IGDB 取得をスキップします。")
            return None

        try:
            # 1. Twitch OAuth2 アクセストークン取得
            with httpx.Client(timeout=10.0) as client:
                token_resp = client.post(
                    "https://id.twitch.tv/oauth2/token",
                    params={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "grant_type": "client_credentials",
                    },
                )
                token_resp.raise_for_status()
                access_token = token_resp.json()["access_token"]

                # 2. IGDB ゲーム検索
                igdb_resp = client.post(
                    "https://api.igdb.com/v4/games",
                    headers={
                        "Client-ID": client_id,
                        "Authorization": f"Bearer {access_token}",
                    },
                    content=f'search "{game_name}"; fields name,summary,storyline; limit 1;',
                )
                igdb_resp.raise_for_status()
                results = igdb_resp.json()

            if not results:
                logger.info("IGDB: ゲーム「%s」が見つかりませんでした。", game_name)
                return None

            game = results[0]
            ctx = GameContext(
                name=game.get("name", game_name),
                summary=game.get("summary"),
                storyline=game.get("storyline"),
                fetched_at=datetime.now(timezone.utc).isoformat(),
            )
            self._data[game_name.lower()] = asdict(ctx)
            self._save()
            logger.info("IGDB: ゲーム「%s」の概要を取得・キャッシュしました。", ctx.name)
            return ctx

        except Exception as exc:
            logger.warning("IGDB 取得に失敗しました: %s", exc)
            return None

    def get_or_fetch(
        self,
        game_name: str,
        client_id: str,
        client_secret: str,
    ) -> GameContext | None:
        """キャッシュを確認し、なければ IGDB から取得する。"""
        cached = self.get(game_name)
        if cached:
            return cached
        if not client_id or not client_secret:
            return None
        return self.fetch_and_cache(game_name, client_id, client_secret)
