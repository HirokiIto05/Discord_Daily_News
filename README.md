# Discord Daily News Bot

このボットは、Discordチャンネルの議論内容を定期的に取得し、OpenAI GPT APIを使用して要約を生成します。

## 機能

- 🔄 **自動要約**: 設定した間隔（デフォルト3時間）でチャンネル内容を自動要約
- 📊 **手動要約**: コマンドによる任意のタイミングでの要約実行
- 💾 **ログ保存**: 要約内容をJSONファイルとして保存
- 📱 **Discord投稿**: 指定チャンネルに要約結果を自動投稿
- 📈 **ステータス確認**: ボットの動作状況を確認

## セットアップ

### 🎯 **超シンプル版（最推奨）**

**リアルタイム通知不要、ファイル保存のみの最小構成**

#### 1. 環境変数の設定

```bash
cp .env.example .env
# .envファイルを編集（DISCORD_BOT_TOKEN, OPENAI_API_KEY, CHANNEL_IDSのみ）
```

#### 2. ワンクリック実行

```bash
# 超簡単実行
./run-simple.sh
```

#### 3. 定期実行（Cron設定）

```bash
# crontabを編集
crontab -e

# 3時間ごとに実行
0 */3 * * * cd /path/to/Discord_Daily_News && ./run-simple.sh
```

**📁 結果**: `summaries/` ディレクトリにJSONファイルで保存

### 🔄 間欠実行モード（Webhook投稿あり）

#### 1. 環境変数の設定

```bash
cp .env.example .env
# .envファイルを編集して必要な値を設定
# DISCORD_WEBHOOK_URL も設定すると結果を自動投稿
```

#### 2. 手動実行（テスト用）

```bash
# スケジューラーを1回実行
./run-scheduler.sh

# または直接Python実行
python scheduler.py
```

#### 3. Cron設定（Linux/Mac）

```bash
# crontabを編集
crontab -e

# 3時間ごとに実行する設定を追加
0 */3 * * * cd /path/to/Discord_Daily_News && ./run-scheduler.sh
```

#### 4. AWS CloudFormation（本格運用）

```bash
# CloudFormationテンプレートでデプロイ
aws cloudformation create-stack \
  --stack-name discord-summarizer \
  --template-body file://aws-cloudformation.yml \
  --capabilities CAPABILITY_IAM \
  --parameters ParameterKey=ECRRepository,ParameterValue=your-ecr-repo
```

### 🤖 常時稼働モード（従来のBot方式）

#### Docker を使用する場合

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

## 🌐 外部サーバーへのデプロイ

### Railway でのデプロイ（推奨）

1. **Railwayアカウント作成**:
   - [Railway](https://railway.app/) でアカウント作成

2. **GitHubリポジトリ接続**:
   - リポジトリをGitHubにプッシュ
   - Railwayで「Deploy from GitHub」を選択

3. **環境変数設定**:
   - Railway ダッシュボードで環境変数を設定
   - `.env.example` の内容を参考に設定

4. **自動デプロイ**:
   - `railway.toml` が自動的に検出されてデプロイ開始

### AWS EC2 でのデプロイ

1. **EC2インスタンス作成**:
   - t3.nano または t2.micro を推奨
   - Ubuntu 22.04 LTS を選択

2. **SSH接続後、スクリプト実行**:
   ```bash
   curl -sSL https://raw.githubusercontent.com/HirokiIto05/Discord_Daily_News/main/deploy-aws.sh | bash
   ```

3. **環境変数設定**:
   ```bash
   nano .env  # 必要な値を設定
   ```

4. **起動**:
   ```bash
   ./deploy.sh
   ```

### VPS（DigitalOcean等）でのデプロイ

1. **Droplet作成**:
   - $4/月のBasicプランで十分
   - Docker対応のイメージを選択

2. **リポジトリクローン**:
   ```bash
   git clone https://github.com/HirokiIto05/Discord_Daily_News.git
   cd Discord_Daily_News
   ```

3. **環境設定 & 起動**:
   ```bash
   cp .env.example .env
   nano .env  # 設定編集
   ./deploy.sh
   ```

## 利用可能なコマンド

- `!summary [チャンネルID] [時間]` - 手動要約実行
  - 例: `!summary 123456789 6` (指定チャンネルの過去6時間を要約)
  - 例: `!summary` (現在のチャンネルの過去3時間を要約)

- `!status` - ボットの動作状況確認

## 💰 運用コストについて

### OpenAI API 料金

**⚠️ OpenAI APIの使用には支払い設定が必要です**

1. **料金体系**:
   - GPT-3.5-turbo: $0.0015/1K tokens (入力) + $0.002/1K tokens (出力)
   - 1回の要約で約500-2000 tokens使用

2. **月額費用の目安**:
   ```
   例：1日20回要約 × 30日 = 600回/月
   費用: 約$1.5-2/月程度
   ```

3. **支払い設定**:
   - [OpenAI Platform Billing](https://platform.openai.com/settings/organization/billing) でクレジットカード登録
   - 使用量制限の設定を推奨

### サーバー費用

**実行方式によってコストが大幅に変わります**

| 実行方式 | サーバー費用 | メリット | デメリット |
|----------|--------------|----------|------------|
| **🎯 超シンプル版（最推奨）** | **$0** | **最小構成、ローカル保存、設定簡単** | **通知なし** |
| 間欠実行（Webhook投稿あり） | $0-1/月 | 低コスト、Discord投稿 | 設定が複雑 |
| 自宅PC Cron | 無料 | コストなし | 停電・障害で停止 |
| AWS Fargate (間欠) | $0.5-1/月 | 安定、従量課金 | 設定が複雑 |
| VPS 常時稼働 | $4-6/月 | 安定稼働 | 24時間課金 |
| AWS EC2 常時稼働 | $3-4/月 | 高信頼性 | 24時間課金 |
| Railway/Render 常時稼働 | $5/月〜 | 簡単デプロイ | 制限あり |

### 推奨構成

**🏆 最もシンプル・コスト効率的**:
- **超シンプル版 + 自宅Cron**: 月額$0（OpenAI APIのみ）
- **設定最小限、通知不要、ファイル保存のみ**

**🔔 Discord通知も必要な場合**:
- 間欠実行 + Webhook: 月額$0-1
- AWS Fargate + EventBridge: 月額$0.5-1

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
