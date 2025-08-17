# Discord Daily News Bot

このボットは、Discordチャンネルの議論内容を定期的に取得し、OpenAI GPT APIを使用して要約を生成します。

## 機能

- 🔄 **自動要約**: 設定した間隔（デフォルト3時間）でチャンネル内容を自動要約
- 📊 **手動要約**: コマンドによる任意のタイミングでの要約実行
- 💾 **ログ保存**: 要約内容をJSONファイルとして保存
- 📱 **Discord投稿**: 指定チャンネルに要約結果を自動投稿
- 📈 **ステータス確認**: ボットの動作状況を確認

## セットアップ

### Docker を使用する場合（推奨）

#### 1. 環境変数の設定

```bash
cp .env.example .env
# .envファイルを編集して必要な値を設定
```

#### 2. Discord Bot & OpenAI API の設定

- [Discord Developer Portal](https://discord.com/developers/applications) でボット作成
- [OpenAI Platform](https://platform.openai.com/api-keys) でAPIキー取得
- `.env` ファイルに必要な情報を設定

#### 3. ビルド & 起動

```bash
# 簡単起動（推奨）
./deploy.sh

# または手動でDocker Compose実行
docker-compose up -d
```

#### 4. 停止

```bash
# 停止
./stop.sh

# ログ付きで停止
./stop.sh --logs

# データクリーンアップ付きで停止
./stop.sh --clean
```

#### 5. ログ確認

```bash
# リアルタイムログ表示
docker-compose logs -f discord-news-bot

# 過去50行のログ表示
docker-compose logs --tail=50 discord-news-bot
```

### 直接Python環境で実行する場合

#### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

#### 2. 環境変数の設定

```bash
cp .env.example .env
# .envファイルを編集
```

#### 3. 実行

```bash
python main.py
```

## 使用方法

### ボットの起動

```bash
python main.py
```

### 利用可能なコマンド

- `!summary [チャンネルID] [時間]` - 手動要約実行
  - 例: `!summary 123456789 6` (指定チャンネルの過去6時間を要約)
  - 例: `!summary` (現在のチャンネルの過去3時間を要約)

- `!status` - ボットの動作状況確認

## 設定項目

`.env` ファイルで以下の項目を設定できます：

- `SUMMARY_INTERVAL_HOURS`: 要約の実行間隔（時間単位、デフォルト: 3）
- `CHANNEL_IDS`: 監視対象チャンネルID（カンマ区切り）
- `SUMMARY_CHANNEL_ID`: 要約結果投稿先チャンネルID

## ファイル構造

```
Discord_Daily_News/
├── main.py              # メインプログラム
├── config.py            # 設定ファイル
├── requirements.txt     # 依存関係
├── Dockerfile           # Dockerイメージ設定
├── docker-compose.yml   # Docker Compose設定
├── .dockerignore        # Docker除外ファイル
├── deploy.sh            # 起動スクリプト
├── stop.sh              # 停止スクリプト
├── .env                 # 環境変数（作成が必要）
├── .env.example         # 環境変数サンプル
├── .gitignore           # Git除外設定
├── logs/                # ログファイル保存ディレクトリ（自動生成）
├── summaries/           # 要約ファイル保存ディレクトリ（自動生成）
└── README.md           # このファイル
```

## ログについて

- アプリケーションログは `discord_news.log` に出力されます
- 要約データは `summaries/` ディレクトリにJSON形式で保存されます

## トラブルシューティング

### よくある問題

1. **ボットがメッセージを取得できない**
   - ボットに適切な権限が付与されているか確認
   - チャンネルIDが正しいか確認

2. **OpenAI APIエラー**
   - APIキーが正しく設定されているか確認
   - API使用量制限に達していないか確認

3. **環境変数エラー**
   - `.env` ファイルが正しく作成されているか確認
   - 必要な環境変数がすべて設定されているか確認

## 注意事項

- ボットのメッセージは要約対象から除外されます
- 大量のメッセージがある場合、OpenAI APIの制限により要約が分割される場合があります
- プライベートチャンネルの場合、ボットに適切な権限を付与する必要があります
