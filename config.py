import os
from dotenv import load_dotenv

load_dotenv()

# Discord設定
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID', 0)) if os.getenv('GUILD_ID', '').strip() else 0

# チャンネルIDまたはチャンネル名の処理
def parse_channel_ids():
    """チャンネルIDまたはチャンネル名を処理"""
    channel_list = []
    raw_channels = os.getenv('CHANNEL_IDS', '').split(',')
    
    for channel in raw_channels:
        channel = channel.strip()
        if not channel:
            continue
            
        # 数値の場合はチャンネルID
        if channel.isdigit():
            channel_list.append(int(channel))
        else:
            # 文字列の場合はチャンネル名として保存（後で解決）
            channel_list.append(channel)
    
    return channel_list

CHANNEL_IDS = parse_channel_ids()
SUMMARY_CHANNEL_ID = int(os.getenv('SUMMARY_CHANNEL_ID', 0)) if os.getenv('SUMMARY_CHANNEL_ID', '').strip().isdigit() else os.getenv('SUMMARY_CHANNEL_ID', '')

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
