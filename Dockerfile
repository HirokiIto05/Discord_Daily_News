# Python 3.11のslimイメージを使用
FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムの更新とタイムゾーン設定
RUN apt-get update && apt-get install -y \
    tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime \
    && echo "Asia/Tokyo" > /etc/timezone

# Pythonの依存関係をコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# ログとデータ保存用のディレクトリを作成
RUN mkdir -p /app/summaries /app/logs

# 非rootユーザーを作成
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# アプリケーションを起動
CMD ["python", "main.py"]
