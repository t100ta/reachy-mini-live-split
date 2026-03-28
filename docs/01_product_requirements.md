# 01. Product Requirements

## 1. 背景

Reachy Mini をいきなり総合的な配信アシスタントにするのではなく、
まずは **Speedrun 配信中の LiveSplit 状態に応じて身体反応を返す相棒** として成立させる。

このフェーズでは、会話品質やチャット応答ではなく、
**安定して反応すること / 身体反応が配信で見て分かること** を重視する。

## 2. プロダクト定義

本アプリは、LiveSplit の timer 状態と split 関連情報を監視し、
Reachy Mini に以下を行わせる。

- run 開始時の「起動」
- run 中の通常待機
- PB ペース時の前向きな反応
- 遅れ時の慎重な反応
- 良い split / 悪い split の瞬間反応
- reset 時の落胆
- 完走時の祝福

## 3. ユーザー像

- 開発者本人が配信者
- 自分で LiveSplit を使う
- Reachy Mini (Wireless) を所有している
- 最初は一人開発で、Claude Code に参照させながら実装する
- 将来的に Twitch / LLM / 配信支援へ拡張する可能性がある

## 4. 初期フェーズの目的

### 必須
- LiveSplit から現在状態を安定取得する
- Reachy Mini の身体反応に落とし込む
- 長時間監視しても破綻しにくい
- 将来の拡張のために、内部イベントを抽象化する

### 今は不要
- 喋ること
- 視聴者との対話
- ゲーム画面理解
- UI の豪華さ

## 5. ユースケース

### UC-01: run 開始
- 配信者が LiveSplit を start する
- アプリが start を検知する
- Reachy Mini が「集中モード」に入る

### UC-02: 通常走行
- run が進行中
- アプリが phase=Running を把握する
- delta に応じて姿勢が変化する

### UC-03: 良い split
- split 直後に delta が改善している
- Reachy Mini が短くうなずく/喜ぶ

### UC-04: 悪い split
- split 直後に delta が悪化している
- Reachy Mini が軽くしょんぼりする

### UC-05: reset
- 配信者が reset する
- Reachy Mini が一瞬落胆してから idle に戻る

### UC-06: 完走
- timer phase が ended になる
- Reachy Mini が祝福モーションを行う

## 6. 機能要件

### FR-01 LiveSplit 接続
- TCP または WebSocket のいずれかで LiveSplit に接続できること
- 既定ポート 16834 を設定で変更可能であること
- 接続失敗時にリトライできること

### FR-02 状態取得
最低限、次を取得すること。
- current timer phase
- split index
- current split name
- current time
- delta
- attempt count

### FR-03 内部イベント変換
LiveSplit の取得値から、次の内部イベントを生成すること。
- run_started
- run_reset
- run_finished
- split_changed
- split_good
- split_bad
- pace_ahead
- pace_behind
- pace_neutral

### FR-04 Reachy モーション実行
- 内部イベントごとにモーションを定義できること
- 継続状態モーションと瞬間イベントモーションを分けること
- モーション切替の過剰なパカつきを抑えること

### FR-05 ログ
- 取得値と発火イベントを JSON Lines で保存すること
- デバッグ用に読みやすいテキストログも出せること

### FR-06 CLI
最低限、以下を持つこと。
- `--dry-run`
- `--config`
- `--log-level`
- `--transport`
- `--host`
- `--port`

## 7. 非機能要件

### NFR-01 安全性
- Reachy が不自然に暴れない
- 例外時は安全姿勢に戻す
- 頻繁なコマンド送信を避ける

### NFR-02 可観測性
- 何を受信し、どう判定し、何を送ったか追える
- 接続断の理由をログで判断できる

### NFR-03 拡張性
- Twitch / LLM / OBS などの新しいイベント源を後で足せる
- 今回は LiveSplit だけでも、内部イベント層を共通化する

### NFR-04 運用性
- 一回のコマンドで起動できる
- dry-run で実機なし検証ができる
- 設定ファイル差し替えだけでペース閾値を調整できる

## 8. スコープ外

- Twitch チャット読み上げ
- ユーザー記憶
- 表情推定
- 音声合成
- Web ダッシュボード
- DB 永続化
- 画像認識でのゲーム状況把握
