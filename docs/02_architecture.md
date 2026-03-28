# 02. Architecture

## 1. 設計方針

初期版は **単一 Python プロセス** で構成する。
ただし、責務は明確に分割する。

目的は、最小構成で動かしつつ、
将来別イベント源を追加できるようにすること。

## 2. 全体構成

```text
LiveSplit
  └─ transport client (TCP / WS)
       └─ polling loop / query loop
            └─ snapshot builder
                 └─ event detector
                      └─ state machine
                           ├─ motion planner
                           ├─ reachy executor
                           └─ logger
```

## 3. レイヤ構成

### 3.1 transport layer
責務:
- LiveSplit への接続
- コマンド送受信
- 再接続
- transport 差異の吸収

候補:
- `LiveSplitTcpClient`
- `LiveSplitWsClient`

初期実装では TCP を本命にする。
理由:
- コマンド仕様が単純
- Python のソケットで十分扱いやすい
- WebSocket 依存を後回しにできる

### 3.2 snapshot layer
責務:
- 1回の観測周期で必要な情報を集めて `LiveSplitSnapshot` を組み立てる

候補項目:
- timer_phase
- split_index
- current_split_name
- current_time
- delta
- attempt_count
- captured_at

### 3.3 event detector
責務:
- 直前 snapshot と現在 snapshot の差から内部イベントを生成する

例:
- phase が NotRunning -> Running になった => `run_started`
- split_index が増えた => `split_changed`
- split_changed かつ delta 改善 => `split_good`

### 3.4 state machine
責務:
- 継続状態を管理する
- 瞬間イベントと継続状態の優先順位を管理する
- 短時間での状態乱高下を防ぐ

### 3.5 motion planner
責務:
- 状態に応じて「どのモーションを実行するか」を決める
- 強い瞬間リアクションと、弱い待機姿勢を分ける
- 実機へ送る前に cooldown / debounce をかける

### 3.6 reachy executor
責務:
- Reachy Mini SDK に対してコマンドを送る
- 実機未接続時は no-op / dry-run にできる
- 安全姿勢への退避を提供する

### 3.7 logging
責務:
- 構造化ログ
- 実行イベントログ
- エラーログ
- セッションログ

## 4. 推奨ポーリング方針

初期版は **pull 型** にする。

理由:
- LiveSplit 側の command interface が明快
- 実装が小さい
- バグ切り分けが簡単

想定周期:
- 4〜10 Hz 程度から開始
- 最初は 5 Hz 推奨

高すぎる頻度は不要。
Reachy のモーションは高フレームで切り替えるものではない。

## 5. データモデル

### 5.1 LiveSplitSnapshot
```python
@dataclass(frozen=True)
class LiveSplitSnapshot:
    captured_at: datetime
    timer_phase: str
    split_index: int
    current_split_name: str | None
    current_time: timedelta | None
    delta: timedelta | None
    attempt_count: int | None
```

### 5.2 InternalEvent
```python
@dataclass(frozen=True)
class InternalEvent:
    name: str
    at: datetime
    payload: dict[str, Any]
```

### 5.3 RuntimeState
```python
@dataclass
class RuntimeState:
    high_level_state: str
    last_motion_name: str | None
    last_motion_at: datetime | None
    last_snapshot: LiveSplitSnapshot | None
    last_split_index: int | None
    pace_bucket: str
```

## 6. 主要な高レベル状態

- idle
- ready
- running_neutral
- running_ahead
- running_behind
- paused
- finished
- disconnected
- safe_mode

瞬間イベントとして:
- run_started
- split_good
- split_bad
- reset
- celebrate

## 7. 重要な設計判断

### AD-01 Python 一本
理由:
- Reachy Mini SDK が Python 中心
- 初期版ではブリッジ不要
- 開発とデバッグが速い

### AD-02 LiveSplit を唯一のイベント源にする
理由:
- 安定した真実の源泉にできる
- 画像認識より保守性が高い
- 配信環境変更の影響を受けにくい

### AD-03 内部イベント層を持つ
理由:
- 将来 Twitch / OBS / LLM を足しても状態機械が流用できる
- テストしやすい

### AD-04 dry-run を最初から入れる
理由:
- Reachy 未接続でも開発できる
- Claude Code が局所修正しやすい
- CI 的な検証を作りやすい

## 8. 例外時の扱い

### LiveSplit 切断
- 状態を `disconnected` にする
- Reachy を大きく動かさない
- 一定間隔で再接続

### Reachy 切断
- イベント処理は継続
- executor が no-op になる
- ログに警告を出す

### 未知の値
- `safe_mode` か `idle` に退避
- 例外でプロセス全体を落とさない

## 9. 将来拡張ポイント

- Twitch イベント source
- LLM based commentator
- 配信後 review job
- Web UI / metrics endpoint
- motion presets の外部ファイル化
