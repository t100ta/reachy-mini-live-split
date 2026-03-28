# 03. State Machine

## 1. 目的

LiveSplit の生値を直接 Reachy に流すのではなく、
一度状態機械で吸収してからモーションを決める。

これにより:
- モーションのパカつき防止
- 条件分岐の整理
- テスト容易性
が得られる。

## 2. 入力

状態機械の入力は以下。

- 最新 `LiveSplitSnapshot`
- 直前 `LiveSplitSnapshot`
- `InternalEvent` 列
- 現在の `RuntimeState`

## 3. 高レベル状態

### idle
- timer が止まっている
- run 未開始
- reset 後の通常待機

### ready
- run 開始直後の短い集中状態
- 数秒後に running_* に遷移

### running_neutral
- run 中
- delta が中立閾値内

### running_ahead
- run 中
- delta が良い側にある

### running_behind
- run 中
- delta が悪い側にある

### paused
- timer paused

### finished
- 完走直後

### disconnected
- LiveSplit に接続できていない

### safe_mode
- 異常時の退避状態

## 4. ペース判定バケット

delta の値から以下の 3 状態に分類する。

- ahead
- neutral
- behind

初期閾値の例:
- ahead: delta <= -1.5 sec
- neutral: -1.5 sec < delta < +1.5 sec
- behind: delta >= +1.5 sec

注:
- 閾値は設定ファイルから変更可能
- ゲームによって別調整できるようにする

## 5. ヒステリシス / デバウンス

状態が細かく行き来しないようにする。

### pace change debounce
- pace bucket の切替は、一定時間以上その条件が続いた時だけ反映
- 例: 1.0〜2.0 秒

### motion cooldown
- 大きい瞬間モーションを短時間で連発しない
- 例: 同種のモーションは 2.0 秒以内に再発火しない

### split priority window
- split 直後は瞬間モーションを優先し、継続状態の上書きを一時停止
- 例: 1.5 秒

## 6. 遷移ルール

### disconnected -> idle
- LiveSplit 再接続成功
- phase が NotRunning

### idle -> ready
- event: `run_started`

### ready -> running_ahead / running_neutral / running_behind
- ready duration 経過
- 最新 pace bucket に応じて遷移

### running_* -> running_*
- pace bucket 変化による遷移
- debounce 後に反映

### running_* -> paused
- phase == Paused

### paused -> running_*
- phase == Running
- pace bucket に応じて復帰

### running_* -> finished
- phase == Ended
- または end 相当イベント

### running_* -> idle
- event: `run_reset`

### finished -> idle
- finish celebration 完了後
- 一定時間経過

### any -> safe_mode
- 致命的な状態不整合
- Reachy 制御例外が連続発生
- 安全退避が必要

## 7. イベント判定ロジック

### run_started
条件:
- prev.timer_phase != "Running"
- curr.timer_phase == "Running"

### run_reset
条件候補:
- running/paused/finished から NotRunning へ遷移
- split_index が -1 に戻る
- current_time が null になる

### split_changed
条件:
- curr.split_index > prev.split_index

### split_good
条件:
- split_changed
- curr.delta が prev.delta より改善
- または curr.delta が ahead 側へ動いた

### split_bad
条件:
- split_changed
- curr.delta が prev.delta より悪化
- または curr.delta が behind 側へ動いた

### run_finished
条件:
- curr.timer_phase == "Ended"
- かつ prev.timer_phase != "Ended"

## 8. 瞬間イベントと継続状態の優先順位

優先順位は以下。

1. 安全退避
2. 接続断
3. finish / reset
4. split_good / split_bad
5. run_started
6. pace based continuous state
7. idle

## 9. 受け入れ観点

- split 時に毎回明確な反応がある
- delta が微小変動してもガチャガチャしない
- reset / finish は見逃しにくい
- 接続断時に落ち着いた安全挙動になる
