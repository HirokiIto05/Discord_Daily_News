#!/bin/bash

# Discord Daily News Bot - Stop Script

set -e

echo "🛑 Discord Daily News Bot - 停止中..."

# コンテナを停止
docker-compose down

echo "✅ ボットが正常に停止されました"

# オプション: ログを表示
if [ "$1" = "--logs" ]; then
    echo "📜 最新のログを表示:"
    echo "----------------------------------------"
    docker-compose logs --tail=50 discord-news-bot
fi

# オプション: データをクリーンアップ
if [ "$1" = "--clean" ]; then
    echo "🧹 データをクリーンアップ中..."
    docker-compose down -v
    docker system prune -f
    echo "✅ クリーンアップが完了しました"
fi
