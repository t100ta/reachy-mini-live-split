# 動作確認手順

## 環境前提

- OS: Windows 11 + WSL2 Ubuntu
- Python: 3.12（mise で管理）
- パッケージ管理: uv
- LiveSplit が Windows 側で起動していること
- LiveSplit: Edit > Control > Start Server で Internal Server を有効にすること

---

## Step 1: 依存パッケージのインストール

```bash
cd /home/tom_t100ta/dev/reachy-mini-live-split

# 通常依存（openai, pygame, websocket-client）
uv sync

# Reachy Mini SDK（実機テスト前に1回だけ）
# ※ pygobject のビルドに cairo 系ライブラリが必要
sudo apt-get install -y libcairo2-dev libgirepository1.0-dev pkg-config
uv pip install reachy_mini

# インストール確認
uv run python -c "import reachy_mini; print('reachy_mini OK')"
uv run python -c "import openai; print('openai OK')"
```

---

## Step 2: 設定ファイル作成

```bash
cp config/app.example.toml config/app.toml
cp config/motions.example.toml config/motions.toml
```

`config/app.toml` の編集箇所:

```toml
[livesplit]
host = "172.23.80.1"   # Windows 側 IP（WSL2 から見た Gateway）

[reachy]
enabled = true
dry_run = false
host = "reachy-mini.local"   # 実機のホスト名または IP
```

LiveSplit の IP は以下で確認:

```bash
ip route show default | awk '{print $3}'
```

---

## Step 3: dry-run で LiveSplit 疎通確認（Reachy 不要）

```bash
uv run python -m app.main --dry-run --config config/app.toml
```

LiveSplit でタイマーを start / split / reset すると、ターミナルにイベントログが流れれば OK。

```
INFO  event=run_started ...
INFO  motion=ready_pose (dry-run)
INFO  event=split_good ...
INFO  motion=split_good_nod (dry-run)
```

---

## Step 4: 実機テスト（Reachy Mini 接続）

```bash
uv run python -m app.main --config config/app.toml
```

初回起動時に HuggingFace から emotions ライブラリ（~160ファイル）をダウンロードします。
2回目以降はキャッシュから即時読み込みます。

### 確認マトリクス

| LiveSplit 操作 | 期待するモーション | 使用 Expression |
|---|---|---|
| Start | ready_pose | `enthusiastic1` |
| Split（ゴールドまたは速い） | split_good_nod | `success1` |
| Split（遅い） | split_bad_droop | `displeased1` |
| Reset | reset_sigh | `frustrated1` |
| Finish | finish_celebrate | `success2` |
| 走行中・ペース良好 | running_ahead_pose | _goto（継続ポーズ） |
| 走行中・ペース悪化 | running_behind_pose | _goto（継続ポーズ） |
| 接続断 | disconnected_pose | _goto（継続ポーズ） |

### 受け入れ条件

- [ ] 5種類以上のモーションが実機で見分けられる
- [ ] Expression フォールバック: Expression 失敗時に goto シーケンスで動く
- [ ] 30分安定稼働（接続断でプロセスが落ちない）
- [ ] Ctrl+C で正常終了し、ロボットが sleep 姿勢になる

---

## ユニットテスト

```bash
uv run pytest tests/ -v
```

36本全 PASS が正常状態。コード変更後は必ず実行すること。

---

## トラブルシューティング

**`reachy_mini` のインストールが失敗する（pycairo ビルドエラー）**

```bash
sudo apt-get install -y libcairo2-dev libgirepository1.0-dev pkg-config
uv pip install reachy_mini
```

**LiveSplit に繋がらない**

```bash
# Windows 側 IP を確認
ip route show default | awk '{print $3}'
# 疎通テスト
curl -s --max-time 2 http://172.23.80.1:16834/livesplit/currenttime
```

**Reachy Mini に繋がらない**

```bash
ping reachy-mini.local
# または IP アドレスで
ping 192.168.x.x
```

**emotions ライブラリのダウンロードが遅い**

初回のみ。HuggingFace からのダウンロードは数十秒〜数分かかります。
`~/.cache/huggingface/` にキャッシュされるため2回目以降は不要。

**pygame の音声初期化エラー（WSL2）**

WSL2 では ALSA デバイスが存在しないため pygame での音声再生はできません。
TTS 音声再生は Web コンソール（ブラウザ経由）を使う設計になっています（実装予定）。
