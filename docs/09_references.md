# 09. References

実装前・実装中に確認すべき外部資料。

## Reachy Mini

- GitHub: `pollen-robotics/reachy_mini`
- Quickstart Guide
- SDK Overview / Python SDK
- AGENTS.md
- Example scripts
- Troubleshooting docs

確認ポイント:
- 推奨接続方法
- `ReachyMini()` の基本利用
- pose / motion 周りの API
- Wireless 実行時の注意
- daemon / desktop app の扱い

## LiveSplit

- GitHub: `LiveSplit/LiveSplit`
- README の "The LiveSplit Server"
- `LiveSplit/LiveSplit.Server` README
- LiveSplit components page
- Commands:
  - `getsplitindex`
  - `getcurrentsplitname`
  - `getcurrenttimerphase`
  - `getcurrenttime`
  - `getdelta`
  - `getattemptcount`
  - `ping`

確認ポイント:
- TCP / WS サーバーの起動方法
- コマンド仕様
- レスポンス形式
- ポート設定
- comparison と delta の扱い

## 実装の考え方

- まず TCP を実装
- snapshot 差分から内部イベントを生成
- Reachy には直接 raw 値を流さない
- dry-run と structured logging を先に入れる
