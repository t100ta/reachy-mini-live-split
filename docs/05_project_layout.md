# 05. Project Layout

## 1. 目的

Claude Code が迷わないよう、最初から責務ごとにファイルを分ける。

## 2. 推奨ディレクトリ構成

```text
project-root/
├─ CLAUDE.md
├─ README.md
├─ pyproject.toml
├─ .python-version              # 任意
├─ .env.example                 # 任意
├─ config/
│  ├─ app.example.toml
│  └─ motions.example.toml
├─ docs/
│  ├─ 01_product_requirements.md
│  ├─ 02_architecture.md
│  ├─ 03_state_machine.md
│  ├─ 04_motion_spec.md
│  ├─ 05_project_layout.md
│  ├─ 06_implementation_plan.md
│  ├─ 07_test_plan.md
│  ├─ 08_operations.md
│  └─ 09_references.md
├─ src/
│  └─ reachy_livesplit/
│     ├─ __init__.py
│     ├─ main.py
│     ├─ cli.py
│     ├─ config.py
│     ├─ logging_setup.py
│     ├─ types.py
│     ├─ clock.py
│     ├─ app.py
│     ├─ transports/
│     │  ├─ __init__.py
│     │  ├─ base.py
│     │  ├─ tcp_client.py
│     │  └─ ws_client.py
│     ├─ livesplit/
│     │  ├─ __init__.py
│     │  ├─ commands.py
│     │  ├─ parser.py
│     │  ├─ poller.py
│     │  └─ snapshot.py
│     ├─ domain/
│     │  ├─ __init__.py
│     │  ├─ events.py
│     │  ├─ event_detector.py
│     │  ├─ state_machine.py
│     │  └─ thresholds.py
│     ├─ motions/
│     │  ├─ __init__.py
│     │  ├─ catalog.py
│     │  ├─ planner.py
│     │  └─ cooldown.py
│     ├─ reachy/
│     │  ├─ __init__.py
│     │  ├─ executor.py
│     │  ├─ real_executor.py
│     │  ├─ dry_executor.py
│     │  └─ safety.py
│     └─ telemetry/
│        ├─ __init__.py
│        ├─ event_log.py
│        └─ session_log.py
└─ tests/
   ├─ test_event_detector.py
   ├─ test_state_machine.py
   ├─ test_thresholds.py
   ├─ test_motion_planner.py
   └─ fixtures/
```

## 3. モジュール責務

### `cli.py`
- 引数解釈

### `config.py`
- TOML 読み込み
- デフォルト値補完
- バリデーション

### `transports/`
- LiveSplit 接続の差異吸収

### `livesplit/poller.py`
- クエリの発行
- snapshot の組み立て

### `domain/event_detector.py`
- snapshot 差分からイベント生成

### `domain/state_machine.py`
- 高レベル状態遷移

### `motions/planner.py`
- state / event から motion command 決定

### `reachy/executor.py`
- Reachy への実際の命令実行
- dry-run 切替

### `telemetry/`
- JSONL ログ
- セッションログ

## 4. 設定ファイル例

### `config/app.example.toml`
```toml
[livesplit]
transport = "tcp"
host = "127.0.0.1"
port = 16834
poll_interval_ms = 200
comparison = "Personal Best"

[thresholds]
ahead_seconds = -1.5
behind_seconds = 1.5
pace_debounce_ms = 1200
motion_cooldown_ms = 2000
split_priority_ms = 1500

[reachy]
enabled = true
dry_run = false

[logging]
level = "INFO"
jsonl_path = "logs/session.jsonl"
```

## 5. 将来の拡張スロット

以下は先にフォルダを作らなくてもよいが、
命名上は足しやすくしておく。

- `sources/twitch/`
- `sources/obs/`
- `review/`
- `memory/`
- `web/`
