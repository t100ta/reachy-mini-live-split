# Reachy Mini × LiveSplit 連携アプリ 開発ドキュメント

このディレクトリは、**Python 前提**で実装する
「LiveSplit の状態に応じて Reachy Mini のモーションを変えるアプリ」
の設計資料一式です。

## 目的

まずは配信サポート全体ではなく、以下の最小スコープに絞る。

- LiveSplit から現在の run 状態を取得する
- その状態を Reachy Mini 用の内部イベントに変換する
- 内部イベントに応じて Reachy Mini の姿勢・短いリアクションを変える
- ログを残し、将来の高度化の土台にする

## このドキュメントの使い方

Claude Code / 人間ともに、次の順で読むことを想定する。

1. `CLAUDE.md`
2. `docs/01_product_requirements.md`
3. `docs/02_architecture.md`
4. `docs/03_state_machine.md`
5. `docs/04_motion_spec.md`
6. `docs/05_project_layout.md`
7. `docs/06_implementation_plan.md`
8. `docs/07_test_plan.md`
9. `docs/08_operations.md`
10. `docs/09_references.md`

## スコープ外

初期フェーズでは次を行わない。

- Twitch チャット連携
- LLM 会話生成
- 画像認識
- OBS 連携
- 音声認識
- 本番中の自己改善
- Reachy 側での複雑な Web UI

## 想定環境

- 開発言語: Python
- 実行環境: Windows 上で LiveSplit、Reachy Mini は同一 LAN 上の Wireless を想定
- Reachy Mini 制御: 公式 Python SDK
- LiveSplit 連携: 内蔵 TCP Server もしくは WebSocket Server
- ログ保存: ローカルファイル（JSON Lines 推奨）

## 成果物の期待値

最低限、以下が動くこと。

- LiveSplit に接続できる
- start / split / reset / end を検知できる
- current split / delta / timer phase を取得できる
- Reachy Mini が状態に応じて明確に異なるモーションを返す
- アプリが落ちても LiveSplit / Reachy 側に危険な状態を残さない
