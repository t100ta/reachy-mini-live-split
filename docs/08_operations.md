# 08. Operations

## 1. 起動前チェック

### LiveSplit 側
- LiveSplit が起動している
- TCP Server または WS Server が起動している
- ポート設定が一致している
- 比較対象が意図したものになっている

### Reachy 側
- 電源が入っている
- 同一ネットワーク上にいる
- SDK 接続できる
- 危険物の近くに置いていない

## 2. 推奨起動モード

### 開発中
- `--dry-run` を基本にする
- poll interval はやや遅めでよい
- console log を verbose にする

### 実機テスト
- 最初は短い時間で確認する
- 1つずつモーションを有効化する
- いきなり長時間配信に投入しない

## 3. 想定トラブルと対処

### LiveSplit に繋がらない
確認:
- server を起動したか
- ポートは 16834 か
- TCP / WS の選択が合っているか

### phase は取れるが delta が変
確認:
- comparison の設定
- run 状態
- split ファイル側の比較条件

### Reachy が動かない
確認:
- SDK 接続
- daemon 状態
- 実機 / シミュレーションの取り違え
- dry-run になっていないか

### Reachy が動きすぎる
確認:
- motion cooldown
- pace debounce
- poll interval
- delta 閾値

## 4. 運用ログ

最低限の出力先:
- console log
- session JSONL
- crash log

ログディレクトリ例:
```text
logs/
  session-2026-03-24T20-30-00.jsonl
  app.log
```

## 5. セーフティ方針

- プログラム終了時は safe pose を送る
- 例外時は可能なら safe pose を送る
- 接続断時は大きい動きを止める
- 連続失敗時は Reachy 制御を一時停止する

## 6. 将来の運用改善

- session replay
- motion tuning dashboard
- run summary report
- per-game config
