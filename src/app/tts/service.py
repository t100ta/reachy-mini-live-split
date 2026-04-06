from __future__ import annotations

import logging
import os

from app.config import TtsConfig
from app.tts.audio_store import AudioStore
from app.tts.game_context import GameContextCache

logger = logging.getLogger(__name__)

_PROMPTS: dict[str, str] = {
    "run_started":  "タイムアタックがスタートした。ゲームの世界観や雰囲気に触れながら、短く応援のひとこと（20字以内、日本語）",
    "split_good":   "スプリット「{split}」を{delta}で通過した。スプリット名やゲームの内容に触れながら、短く明るいひとこと（20字以内、日本語）",
    "split_bad":    "スプリット「{split}」が{delta}遅れた。スプリット名やゲームの内容に触れながら、短く励ましのひとこと（20字以内、日本語）",
    "run_finished": "タイムアタックが完走した。ゲームの世界観に触れながら、短く喜びのひとこと（20字以内、日本語）",
    "run_reset":    "リセットした。ゲームやスピードランの文脈に触れながら、短く慰めのひとこと（20字以内、日本語）",
}


def _fmt_delta(delta: float | None) -> str:
    if delta is None:
        return "不明"
    sign = "+" if delta >= 0 else "-"
    abs_d = abs(delta)
    m = int(abs_d // 60)
    s = abs_d % 60
    if m > 0:
        return f"{sign}{m}分{s:.1f}秒"
    return f"{sign}{s:.1f}秒"


class TTSService:
    def __init__(self, cfg: TtsConfig) -> None:
        self._cfg = cfg
        self._store = AudioStore(cfg.audio_path)
        self._game_cache = GameContextCache(cfg.game_cache_path)

        # LLM によるテキスト生成は常に OpenAI を使用
        api_key = cfg.openai_api_key or os.environ.get("OPENAI_API_KEY", "")
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)

        if cfg.engine == "coeiroink":
            self._coeiroink_init()

    def _coeiroink_init(self) -> None:
        """COEIROINK の話者一覧を取得し、設定した話者の UUID と styleId を解決する。"""
        import httpx
        try:
            resp = httpx.get(f"{self._cfg.coeiroink_url}/v1/speakers", timeout=5.0)
            resp.raise_for_status()
            speakers = resp.json()
        except Exception as exc:
            raise RuntimeError(f"COEIROINK への接続に失敗しました: {exc}") from exc

        target_name = self._cfg.coeiroink_speaker_name
        target_style = self._cfg.coeiroink_style_name

        for speaker in speakers:
            if speaker.get("speakerName") == target_name:
                for style in speaker.get("styles", []):
                    if not target_style or style.get("styleName") == target_style:
                        self._coeiroink_uuid = speaker["speakerUuid"]
                        self._coeiroink_style_id = style["styleId"]
                        logger.info(
                            "COEIROINK: 話者「%s / %s」(uuid=%s, styleId=%d) を使用します。",
                            target_name, style.get("styleName"),
                            self._coeiroink_uuid, self._coeiroink_style_id,
                        )
                        return
        raise RuntimeError(
            f"COEIROINK: 話者「{target_name}」スタイル「{target_style}」が見つかりません。"
        )

    def generate(
        self,
        event_name: str,
        split_name: str | None,
        delta: float | None,
        game_name: str | None = None,
        category_name: str | None = None,
    ) -> tuple[str, float, str]:
        """
        LLM でひとこと生成 → TTS で音声合成。
        Returns: (ファイル名, 推定再生秒数, テキスト)
        """
        text = self._generate_text(event_name, split_name, delta, game_name, category_name)
        logger.info("TTS コメント: %s", text)
        filename = self._synthesize(text)
        duration = max(1.0, len(text) * 0.15)
        return filename, duration, text

    def _build_system_message(
        self,
        game_name: str | None,
        category_name: str | None,
    ) -> str:
        """LLM の system メッセージを組み立てる。"""
        personality = (
            "あなたはスピードランナーの傍らで見守る、落ち着いた性格のロボットの相棒です。"
            "一喜一憂せず、温かく穏やかに、でも的確に一言添えるスタイルです。"
            "ハイテンションな煽りや大げさな表現は避け、静かな共感や小さな励ましを大切にしてください。"
            "コメントにはスプリット名やゲームの世界観・登場人物・雰囲気を積極的に盛り込み、"
            "そのゲームを知っている人が聞いてニヤリとできるような内容にしてください。"
        )

        if not game_name:
            return personality

        parts = [personality, f" 今プレイしているゲームは「{game_name}」"]
        if category_name:
            parts.append(f"（{category_name}）")
        parts.append("です。")

        # IGDB からゲームコンテキストを取得
        ctx = self._game_cache.get_or_fetch(
            game_name,
            self._cfg.igdb_client_id,
            self._cfg.igdb_client_secret,
        )
        if ctx:
            if ctx.summary:
                parts.append(f" ゲーム概要: {ctx.summary}")
            if ctx.storyline:
                parts.append(f" ストーリー: {ctx.storyline}")

        return "".join(parts)

    def _generate_text(
        self,
        event_name: str,
        split_name: str | None,
        delta: float | None,
        game_name: str | None = None,
        category_name: str | None = None,
    ) -> str:
        tmpl = _PROMPTS.get(event_name)
        if tmpl is None:
            return "ファイト！"
        prompt = tmpl.format(
            split=split_name or "不明",
            delta=_fmt_delta(delta),
        )
        system_msg = self._build_system_message(game_name, category_name)
        try:
            resp = self._client.chat.completions.create(
                model=self._cfg.llm_model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=40,
                temperature=0.9,
            )
            return resp.choices[0].message.content.strip()
        except Exception as exc:
            logger.warning("LLM 生成に失敗しました: %s", exc)
            return "ファイト！"

    def _synthesize(self, text: str) -> str:
        if self._cfg.engine == "coeiroink":
            return self._synthesize_coeiroink(text)
        return self._synthesize_openai(text)

    def _synthesize_openai(self, text: str) -> str:
        try:
            resp = self._client.audio.speech.create(
                model=self._cfg.tts_model,
                voice=self._cfg.tts_voice,
                input=text,
            )
            return self._store.save(resp.content, suffix=".mp3")
        except Exception as exc:
            logger.warning("OpenAI TTS 合成に失敗しました: %s", exc)
            raise

    def _synthesize_coeiroink(self, text: str) -> str:
        import httpx
        body = {
            "speakerUuid": self._coeiroink_uuid,
            "styleId": self._coeiroink_style_id,
            "text": text,
            "speedScale": 1.0,
            "volumeScale": 1.0,
            "pitchScale": 0.0,
            "intonationScale": 1.0,
            "prePhonemeLength": 0.1,
            "postPhonemeLength": 0.5,
            "outputSamplingRate": 24000,
            "prosodyDetail": [],
            "adjustedF0": [],
            "processingAlgorithm": "coeiroink",
        }
        try:
            resp = httpx.post(
                f"{self._cfg.coeiroink_url}/v1/synthesis",
                json=body,
                timeout=15.0,
            )
            resp.raise_for_status()
            return self._store.save(resp.content, suffix=".wav")
        except Exception as exc:
            logger.warning("COEIROINK TTS 合成に失敗しました: %s", exc)
            raise
