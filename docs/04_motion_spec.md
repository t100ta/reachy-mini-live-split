# 04. Motion Spec

## 1. 基本方針

モーションは「派手さ」より「配信で読み取れる差」を優先する。

初期版では、以下を守る。

- 1モーションは短く
- 大きく振り回さない
- 区別しやすい
- 連発しても鬱陶しくなりにくい
- 安全姿勢へ戻れる

## 2. モーションの分類

### continuous pose
継続状態を表す弱い姿勢。
例:
- idle_pose
- running_neutral_pose
- running_ahead_pose
- running_behind_pose
- disconnected_pose

### impulse motion
瞬間イベントに反応する短い動き。
例:
- start_nod
- split_good_nod
- split_bad_droop
- reset_sigh
- finish_celebrate

## 3. 初期モーション一覧

### M-01 idle_pose
用途:
- 待機
特徴:
- 正面
- 微小動作のみ
長さ:
- 継続

### M-02 ready_pose
用途:
- run 開始直後
特徴:
- やや前のめり
- 少し緊張感
長さ:
- 1〜2秒

### M-03 running_neutral_pose
用途:
- 通常走行
特徴:
- 落ち着いた追従
- 目立ちすぎない

### M-04 running_ahead_pose
用途:
- PB ペース良好
特徴:
- ほんの少し前のめり
- 明るい印象
注意:
- 喜びすぎない

### M-05 running_behind_pose
用途:
- PB ペース悪化
特徴:
- わずかに首を傾ける
- 慎重な印象
注意:
- 悲壮感を出しすぎない

### M-06 split_good_nod
用途:
- 良い split
特徴:
- 小さく気持ちよい頷き
長さ:
- 0.5〜1.2秒

### M-07 split_bad_droop
用途:
- 悪い split
特徴:
- 一瞬だけしょんぼり
長さ:
- 0.6〜1.2秒

### M-08 reset_sigh
用途:
- reset
特徴:
- 一瞬脱力してから戻る
長さ:
- 0.8〜1.5秒

### M-09 finish_celebrate
用途:
- 完走
特徴:
- 明確に嬉しいと分かる
- ただし長すぎない
長さ:
- 1.5〜3秒

### M-10 disconnected_pose
用途:
- LiveSplit 切断時
特徴:
- 控えめ
- ほぼ待機

## 4. モーション設計原則

### 原則1
継続状態と瞬間イベントを混ぜない。

### 原則2
瞬間イベント後は継続状態へ復帰する。

### 原則3
同じイベントでも連発を抑える。

### 原則4
可読性を優先し、細かすぎる差分は避ける。

## 5. 実装形式

初期版では、モーションは以下のいずれかで表現する。

- Python 内で pose target を直接定義
- シンプルな関数として実装
- 将来は YAML/JSON 化可能な構造を意識する

例:
```python
@dataclass(frozen=True)
class MotionCommand:
    name: str
    duration_s: float
    pose: str
    priority: int = 0
```

## 6. 禁止事項

- 高頻度で大角度を繰り返す
- split ごとに過剰な celebration を入れる
- 例外時に姿勢が中途半端なまま止まる
- LiveSplit の微小変動で毎秒モーションが変わる

## 7. 調整パラメータ

設定ファイルから変更可能にするもの:
- ahead / behind 閾値
- motion cooldown
- pace change debounce
- finish celebration duration
- split reaction duration
- motion enable/disable

## 8. Dry-run 表現

実機がない場合でも、
次のような形で出力して検証できるようにする。

```text
[Motion] split_good_nod
[State] running_ahead
[Delta] -00:01.42
```
