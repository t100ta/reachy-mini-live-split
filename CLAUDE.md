# Claude Code 作業指示

このリポジトリでは、**Reachy Mini × LiveSplit 連携アプリ**を Python で実装する。

まずこのファイルを読み、その後に `docs/` 配下を読むこと。

## 最重要方針

- いきなり完成品を作らない
- 最初は **LiveSplit を唯一のイベント源** とする
- Twitch / LLM / 画像認識 / OBS は後回し
- Reachy Mini の身体反応を作ることを最優先にする
- Python だけで完結させる
- まず動く最小構成を作ってから広げる

## 実装対象

初期実装の責務は以下に限定する。

1. LiveSplit との接続
2. LiveSplit 状態の取得
3. 取得値を内部イベントへ変換
4. 状態機械による Reachy Mini モーション切替
5. ログ保存
6. 最低限の設定ファイル読み込み
7. 最低限の CLI

## 実装しないもの

このフェーズでは以下を作らない。

- Twitch API / IRC / EventSub
- LLM 連携
- チャット記憶
- 自己改善ループ
- 画像認識
- 音声合成
- Web UI
- 配信オーバーレイ
- データベース

## 参考にすべき外部資料

実装前に、Reachy Mini の公式 AI エージェント向けガイドと SDK / Quickstart を確認すること。
また LiveSplit の README にある internal server の仕様を確認すること。

優先順位:
1. Reachy Mini 公式 AGENTS.md
2. Reachy Mini 公式 Quickstart / Python SDK
3. LiveSplit 公式 README（internal server）
4. 本ディレクトリの docs

## 実装姿勢

- まず CLI だけで LiveSplit のイベント監視を完成させる
- Reachy 未接続でも dry-run できるようにする
- モーションは最初から凝りすぎない
- 例外時は安全側に倒す
- 長時間監視前提で、接続断に耐える
- ログで原因追跡できるようにする

## コーディング方針

- 型ヒントを付ける
- dataclass を優先する
- 小さな責務でモジュールを分ける
- 外部依存を増やしすぎない
- 非同期が必要な箇所だけ `asyncio` を使う
- LiveSplit との通信と Reachy 制御を分離する
- 1ファイル巨大化を避ける

## 受け入れ条件

以下を満たしたら初期実装として十分。

- `python -m app.main --dry-run` で LiveSplit イベント監視が動く
- timer phase / split index / split name / delta が取れる
- `start`, `split_good`, `split_bad`, `ahead`, `behind`, `reset`, `finished`
  の主要イベントが内部で発火する
- Reachy 接続時に少なくとも 5 種類以上の見分けやすいモーションが動く
- 接続断や例外時にプロセスが無限暴走しない
