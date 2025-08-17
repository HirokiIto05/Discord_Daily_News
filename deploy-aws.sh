# AWS EC2デプロイ用スクリプト

#!/bin/bash

# EC2インスタンスでの初期設定とデプロイ

echo "🚀 AWS EC2でのDiscord Daily News Bot セットアップ"

# システム更新
sudo apt update && sudo apt upgrade -y

# Dockerインストール
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Docker Composeインストール
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# リポジトリクローン
git clone https://github.com/HirokiIto05/Discord_Daily_News.git
cd Discord_Daily_News

# 環境変数設定
echo "📝 .envファイルを設定してください:"
cp .env.example .env
nano .env

# デプロイ
echo "🚀 ボットを起動しています..."
./deploy.sh

echo "✅ セットアップ完了！"
echo "📊 ログ確認: docker-compose logs -f discord-news-bot"
