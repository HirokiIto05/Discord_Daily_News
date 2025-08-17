#!/bin/bash

# Discord要約シンプルスケジューラー実行スクリプト

set -e

echo "📝 Discord要約システム（シンプル版）を実行中..."

# .envファイルの存在確認
if [ ! -f .env ]; then
    echo "❌ .envファイルが見つかりません"
    echo "💡 cp .env.example .env でファイルを作成し、設定を編集してください"
    exit 1
fi

# 必要なディレクトリを作成
mkdir -p summaries

# 実行方法を選択
if command -v docker &> /dev/null; then
    echo "🐳 Dockerで実行します..."
    
    # Dockerイメージをビルド
    docker build -f Dockerfile.simple -t discord-simple-summarizer .
    
    # コンテナを実行
    docker run --rm \
        --env-file .env \
        -v "$(pwd)/summaries:/app/summaries" \
        -v "$(pwd)/last_run.json:/app/last_run.json" \
        discord-simple-summarizer
        
elif command -v python3 &> /dev/null; then
    echo "🐍 Pythonで直接実行します..."
    
    # 依存関係をチェック
    if ! python3 -c "import aiohttp, aiofiles, openai" 2>/dev/null; then
        echo "📦 依存関係をインストール中..."
        pip3 install -r requirements.txt
    fi
    
    # シンプルスケジューラーを実行
    python3 simple_scheduler.py
    
else
    echo "❌ DockerまたはPython3が必要です"
    exit 1
fi

# 実行結果を確認
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 要約が正常に完了しました！"
    echo "📁 要約ファイル:"
    ls -la summaries/ | tail -n 5
    echo ""
    echo "📊 最新の要約内容:"
    latest_file=$(ls -t summaries/*.json 2>/dev/null | head -n 1)
    if [ -n "$latest_file" ]; then
        echo "ファイル: $latest_file"
        # 要約部分のみ表示
        cat "$latest_file" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'チャンネル: {data[\"channel_name\"]}')
print(f'メッセージ数: {data[\"messages_count\"]}件')
print(f'要約: {data[\"summary\"][:200]}...')
"
    fi
else
    echo "❌ 要約の実行中にエラーが発生しました"
    exit 1
fi

echo ""
echo "🎉 シンプルスケジューラー実行完了"
echo "💡 定期実行するには Cron で以下を設定:"
echo "   0 */3 * * * cd $(pwd) && ./run-simple.sh"
