#!/bin/bash

# Discord Daily News Bot - Build & Deploy Script

set -e

echo "🚀 Discord Daily News Bot - ビルド & デプロイ開始"

# .envファイルの存在確認
if [ ! -f .env ]; then
    echo "❌ .envファイルが見つかりません"
    echo "📝 .env.exampleをコピーして.envファイルを作成し、必要な環境変数を設定してください"
    exit 1
fi

# 必要なディレクトリを作成
echo "📁 必要なディレクトリを作成中..."
mkdir -p logs summaries

# Dockerイメージをビルド
echo "🔨 Dockerイメージをビルド中..."
docker-compose build

# コンテナを起動
echo "🚀 コンテナを起動中..."
docker-compose up -d

# 起動状況を確認
echo "📊 コンテナの状況を確認中..."
sleep 5
docker-compose ps

# ログを表示
echo "📜 ボットログを表示（Ctrl+Cで終了）:"
echo "----------------------------------------"
docker-compose logs -f discord-news-bot
