import os
from dotenv import load_dotenv

load_dotenv()

# Discord設定
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', 0))
CHANNEL_IDS = [int(id.strip()) for id in os.getenv('CHANNEL_IDS', '').split(',') if id.strip()]
SUMMARY_CHANNEL_ID = int(os.getenv('SUMMARY_CHANNEL_ID', 0))

# OpenAI設定
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# スケジュール設定
SUMMARY_INTERVAL_HOURS = int(os.getenv('SUMMARY_INTERVAL_HOURS', 3))

# 要約設定
MAX_MESSAGES_PER_CHANNEL = 100  # チャンネルごとの最大メッセージ数
SUMMARY_PROMPT = """
以下のDiscordチャンネルでの議論内容を日本語で要約してください。
重要なポイント、決定事項、議論の流れを分かりやすくまとめてください。

チャンネル名: {channel_name}
期間: {start_time} から {end_time} まで

メッセージ:
{messages}

要約:
"""
