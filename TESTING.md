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

# 通常依存（fastapi, uvicorn, openai, websocket-client）
uv sync

# Reachy Mini SDK（実機テスト前に1回だけ）
# ※ pygobject のビルドに cairo 系ライブラリが必要
sudo apt-get install -y libcairo2-dev libgirepository1.0-dev pkg-config
uv pip install reachy_mini

# インストール確認
uv run python -c "import reachy_mini; print('reachy_mini OK')"
uv run python -c "import openai, fastapi, uvicorn; print('web/tts deps OK')"
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

[web]
enabled = true
host = "0.0.0.0"
port = 8765

[tts]
enabled = true
engine = "openai"              # "openai" | "coeiroink"
openai_api_key = ""            # 空なら環境変数 OPENAI_API_KEY を使用
# COEIROINK を使う場合は下記も設定（engine = "coeiroink" に変更）
# coeiroink_url = "http://172.23.80.1:50032"
# coeiroink_speaker_name = "茅冬生すずな"
# coeiroink_style_name = "のーまる"
# IGDB ゲームコンテキスト（任意）
# igdb_client_id = ""          # 空なら IGDB 取得をスキップ
# igdb_client_secret = ""
```

LiveSplit の IP 確認:

```bash
ip route show default | awk '{print $3}'
```

環境変数での認証情報設定:

```bash
export OPENAI_API_KEY="sk-..."
export IGDB_CLIENT_ID="..."
export IGDB_CLIENT_SECRET="..."
```

---

## Step 3: dry-run で LiveSplit 疎通確認（Reachy 不要）

```bash
uv run python -m app.main --dry-run --config config/app.toml
```

LiveSplit でタイマーを start / split / reset すると、ターミナルにイベントログが流れれば OK。

---

## Step 4: Web コンソール確認

`config/app.toml` の `[web] enabled = true` にして起動:

```bash
uv run python -m app.main --dry-run --config config/app.toml
```

ブラウザで `http://localhost:8765` を開く。

> **WSL2 からアクセスできない場合:**
> WSL2 の IP を確認してブラウザから `http://<WSL2のIP>:8765` でアクセス:
>
> ```bash
> ip addr show eth0 | grep "inet " | awk '{print $2}'
> ```
>
> または Windows 側でポートフォワードを設定:
>
> ```
> netsh interface portproxy add v4tov4 listenport=8765 listenaddress=0.0.0.0 connectport=8765 connectaddress=<WSL2のIP>
> ```

LiveSplit 操作でイベントがブラウザに流れることを確認:

- [ ] `start` → 右上「🔊 クリックして音声を有効化」ボタンが表示される
- [ ] `split_good` → 緑フラッシュ + イベントログに追記
- [ ] `split_bad` → 赤フラッシュ
- [ ] `reset` → 黄フラッシュ

> **注意（通常ブラウザ）:** ページを開いたら最初に「🔊 クリックして音声を有効化」ボタンを押してください。  
> **OBS ブラウザソースでは不要**（自動で有効化されます）。

---

## Step 5: TTS 確認

### 5a. OpenAI エンジン

`[tts] enabled = true` / `engine = "openai"` にして起動（`OPENAI_API_KEY` が必要）:

```bash
uv run python -m app.main --dry-run --config config/app.toml
```

確認チェックリスト:

- [ ] LiveSplit でタイマーを **スタート** → 2〜4秒後にブラウザから応援コメントが流れる（`run_started` イベント）
- [ ] **split_good** → 明るいコメント音声が流れる
- [ ] **split_bad** → 励ましコメント音声が流れる
- [ ] **reset** → 慰めコメント音声が流れる
- [ ] **finish** → 喜びコメント音声が流れる
- [ ] TTS 再生中にターミナルの `[Motion] talking_pose` が出る
- [ ] ログに `TTS コメント:` が出ており、ゲーム名が含まれている（LiveSplit でゲーム名設定済みの場合）

### TTS フロー

```
スプリットイベント発生
    → OpenAI gpt-4o-mini でひとこと生成（ゲーム名・カテゴリ・IGDB概要をコンテキストとして注入）
    → OpenAI TTS API で mp3 合成
    → ブラウザに play_audio メッセージ送信
    → Web Audio API で再生
    → 再生中は Reachy Mini が talking_pose を実行
    → 再生終了で通常ポーズに戻る
```

### 5b. COEIROINK エンジン（任意）

**事前準備:**
1. Windows 側で COEIROINK を起動
2. 茅冬生すずな（MYCOEIROINK）ボイスモデルをインストール
3. COEIROINK の起動確認（ブラウザで `http://127.0.0.1:50032/docs` が開けること）

`config/app.toml` を変更:

```toml
[tts]
enabled = true
engine = "coeiroink"
coeiroink_url = "http://172.23.80.1:50032"   # Windows 側 IP
coeiroink_speaker_name = "茅冬生すずな"
coeiroink_style_name = "のーまる"
```

起動ログで話者解決を確認:

```
COEIROINK: 話者「茅冬生すずな / のーまる」(uuid=..., styleId=...) を使用します。
```

- [ ] スプリット時に茅冬生すずなの音声が流れる
- [ ] `logs/audio/` に `.wav` ファイルが生成される

> **クレジット義務:** COEIROINK + 茅冬生すずなを使用する配信の概要欄等に  
> `COEIROINK:茅冬生すずな` と記載すること（COEIROINK 規約）。

### 5c. IGDB ゲームコンテキスト（任意）

[Twitch Dev Console](https://dev.twitch.tv/console) でアプリ登録（無料）して Client ID / Secret を取得。

```toml
[tts]
igdb_client_id = "${IGDB_CLIENT_ID}"
igdb_client_secret = "${IGDB_CLIENT_SECRET}"
```

LiveSplit でゲーム名が設定されていると、初回スプリット時に IGDB からゲーム概要を取得してキャッシュします。

```bash
# キャッシュ確認
cat logs/game_cache.json
```

- [ ] `logs/game_cache.json` にゲーム情報が保存される
- [ ] TTS コメントの内容がゲームのストーリー・概要を反映している

---

## Step 6: 実機テスト（Reachy Mini 接続）

```bash
uv run python -m app.main --config config/app.toml
```

初回起動時に HuggingFace から emotions ライブラリ（~160ファイル）をダウンロードします。
2回目以降はキャッシュから即時読み込みます。

### 確認マトリクス

| LiveSplit 操作              | 期待するモーション  | 使用 Expression        |
| --------------------------- | ------------------- | ---------------------- |
| Start                       | ready_pose          | `enthusiastic1`        |
| Split（ゴールドまたは速い） | split_good_nod      | `success1`             |
| Split（遅い）               | split_bad_droop     | `displeased1`          |
| Reset                       | reset_sigh          | `frustrated1`          |
| Finish                      | finish_celebrate    | `success2`             |
| TTS 再生中                  | talking_pose        | \_goto（アンテナ交互） |
| 走行中・ペース良好          | running_ahead_pose  | \_goto（継続ポーズ）   |
| 走行中・ペース悪化          | running_behind_pose | \_goto（継続ポーズ）   |
| 接続断                      | disconnected_pose   | \_goto（継続ポーズ）   |

### 受け入れ条件

- [ ] 5種類以上のモーションが実機で見分けられる
- [ ] スタート時に TTS コメントが流れる
- [ ] TTS 再生中に talking_pose が動く
- [ ] TTS 再生終了後に通常ポーズに戻る
- [ ] 30分安定稼働（接続断でプロセスが落ちない）
- [ ] Ctrl+C で正常終了し、ロボットが sleep 姿勢になる

---

## OBS 設定

1. OBS のソース追加 → **ブラウザ**
2. URL: `http://localhost:8765`（または WSL2 の IP）
3. 幅: `1920`、高さ: `180`（横長バー）
4. **「ページのオーディオを制御する」を有効化**（音声キャプチャに必要）
5. **「シーンがアクティブでない場合にソースをシャットダウン」をオフ**（音声のみ使いたい場合）
6. 背景を透過したい場合: カスタム CSS に `body { background: transparent !important; }`

---

## ユニットテスト

```bash
uv run pytest tests/ -v
```

全 PASS が正常状態。コード変更後は必ず実行すること。

---

## トラブルシューティング

**`reachy_mini` のインストールが失敗する（pycairo ビルドエラー）**

```bash
sudo apt-get install -y libcairo2-dev libgirepository1.0-dev pkg-config
uv pip install reachy_mini
```

**LiveSplit に繋がらない**

```bash
ip route show default | awk '{print $3}'
curl -s --max-time 2 http://172.23.80.1:16834/livesplit/currenttime
```

**Web コンソールにアクセスできない（WSL2）**

```bash
# WSL2 の IP を確認
ip addr show eth0 | grep "inet " | awk '{print $2}'
# http://<上記IP>:8765 でアクセス
```

**スタート時に TTS が流れない**

- `comment_events` に `"run_started"` が含まれているか確認
- `[tts] enabled = true` になっているか確認

**TTS が遅い / 失敗する（OpenAI）**

- `OPENAI_API_KEY` が正しく設定されているか確認
- ネットワーク接続を確認
- `[tts] enabled = false` にしてコメントなしで動作確認

**COEIROINK に繋がらない**

- COEIROINK が Windows 側で起動しているか確認（`http://127.0.0.1:50032/docs`）
- `coeiroink_url` が WSL2 から見た Windows IP になっているか確認（`http://172.23.80.1:50032`）
- 話者名・スタイル名のスペルが正確か確認（`/v1/speakers` のレスポンスと照合）

**IGDB 取得に失敗する**

- `igdb_client_id` / `igdb_client_secret` が正しく設定されているか確認
- IGDB 未設定でもゲームコンテキストなしで動作する（警告ログのみ）

**emotions ライブラリのダウンロードが遅い**
初回のみ。`~/.cache/huggingface/` にキャッシュされるため2回目以降は不要。
