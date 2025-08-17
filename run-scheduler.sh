#!/bin/bash

# Discord要約スケジューラー実行スクリプト

set -e

echo "🕐 Discord要約スケジューラーを実行中..."

# .envファイルの存在確認
if [ ! -f .env ]; then
    echo "❌ .envファイルが見つかりません"
    exit 1
fi

# 必要なディレクトリを作成
mkdir -p summaries

# スケジューラーを実行
docker-compose -f docker-compose.scheduler.yml build
docker-compose -f docker-compose.scheduler.yml up --rm

# 実行結果を確認
if [ $? -eq 0 ]; then
    echo "✅ 要約が正常に完了しました"
    echo "📁 要約ファイル: $(ls -la summaries/ | tail -n 5)"
else
    echo "❌ 要約の実行中にエラーが発生しました"
    exit 1
fi

echo "🎉 スケジューラー実行完了"
