# 06. Implementation Plan

## 1. 実装順の原則

- まず LiveSplit 監視だけ通す
- その後 Reachy dry-run
- 最後に実機モーション
- 途中段階でも常に動作確認可能にする

## 2. マイルストーン

### M1: CLI + LiveSplit 接続
成果:
- TCP 接続できる
- `ping` が返る
- コマンド送信のユーティリティができる

完了条件:
- `python -m reachy_livesplit.main --dry-run` で接続確認できる

### M2: Snapshot Poller
成果:
- phase / split index / split name / current time / delta / attempt count を取得できる
- 一定周期で snapshot を表示できる

完了条件:
- 5分程度連続実行しても大きく崩れない

### M3: Event Detector
成果:
- run_started / split_changed / split_good / split_bad / reset / finished を出せる

完了条件:
- テストフィクスチャで主要ケースが通る

### M4: State Machine
成果:
- idle / ready / running_* / finished / disconnected を扱える
- デバウンスが効く

完了条件:
- delta の小刻み変動で状態が暴れない

### M5: Motion Planner + Dry Executor
成果:
- 実機なしでも motion command が可視化できる

完了条件:
- 典型シナリオのログを読んで動きが想像できる

### M6: Reachy Real Executor
成果:
- 実機に pose / simple motion を送れる
- 安全姿勢へ戻せる

完了条件:
- start / split / reset / end が見分けられる動きになる

### M7: ログ整備
成果:
- JSONL ログ
- 人間向け console ログ
- session summary

完了条件:
- 不具合時に「どこで変になったか」を追跡できる

## 3. 最初のタスク分割

### Task 1
`pyproject.toml` と package skeleton を作る

### Task 2
設定読み込みと CLI を作る

### Task 3
LiveSplit TCP client を作る

### Task 4
コマンド群と parser を作る

### Task 5
snapshot poller を作る

### Task 6
event detector を作る

### Task 7
state machine を作る

### Task 8
motion planner を作る

### Task 9
dry executor を作る

### Task 10
real executor を作る

### Task 11
テストを書く

## 4. 実装上の注意

### 注意1
最初から WS と TCP の両対応を作らなくてもよい。
TCP を完成させてから WS を足す。

### 注意2
Reachy がなくても、domain / poller / planner は完成できる。

### 注意3
モーションは凝りすぎず、判別可能性を優先する。

### 注意4
delta の解釈は null を許容する。
序盤や比較条件によっては取得値が無効なことがある。

### 注意5
長期的には comparison を設定可能にする。
初期値は Personal Best でよい。

## 5. 将来の第2フェーズ

- motion の外部定義化
- TCP / WS 両対応
- 簡易 Web UI
- Twitch イベントの追加
- 配信後 review job
