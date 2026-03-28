# 07. Test Plan

## 1. テスト方針

Reachy 実機依存を減らし、まずは
**snapshot -> event -> state -> motion**
の純粋ロジックを十分にテストする。

## 2. テスト対象

### 単体テスト
- command parser
- time parser
- event detector
- thresholds
- state machine
- motion planner

### 結合テスト
- LiveSplit transport mock + snapshot poller
- state machine + motion planner
- dry executor

### 手動テスト
- 実 LiveSplit 接続
- 実 Reachy 接続
- 長時間 run 監視

## 3. 単体テスト観点

### event detector
- NotRunning -> Running で run_started
- split index 増加で split_changed
- split 時の delta 改善で split_good
- split 時の delta 悪化で split_bad
- Running -> NotRunning で reset
- Running -> Ended で finished

### state machine
- ready duration 後に running_* へ移る
- pace が前後しても debounce まで切り替わらない
- reset で idle に戻る
- disconnected で disconnected に入る

### motion planner
- split_good 時に good reaction を選ぶ
- running_ahead で ahead pose を選ぶ
- cooldown 中は同系モーションを抑止する

## 4. 手動テストシナリオ

### Scenario A: start
1. LiveSplit 起動
2. app 起動
3. start
期待:
- run_started 発火
- ready_pose
- running_* に遷移

### Scenario B: good split
1. split 実行
2. delta 改善
期待:
- split_changed
- split_good
- split_good_nod

### Scenario C: bad split
1. split 実行
2. delta 悪化
期待:
- split_bad_droop

### Scenario D: reset
1. running 中に reset
期待:
- reset_sigh
- idle に戻る

### Scenario E: finish
1. 完走
期待:
- finish_celebrate
- finished -> idle

### Scenario F: disconnect
1. LiveSplit を閉じる
期待:
- disconnected state
- 暴れない
- 再接続待機

## 5. ログ確認項目

各主要イベントで以下が残ること。

- timestamp
- raw snapshot
- detected events
- high level state
- motion command
- transport status

## 6. 受け入れテスト

初期版は次を満たせばよい。

- 30分程度の配信前テストで安定
- split / reset / finish が見逃されにくい
- モーションがうるさすぎない
- 実機なしでもロジック検証可能
