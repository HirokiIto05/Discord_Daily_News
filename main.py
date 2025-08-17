import discord
from discord.ext import commands, tasks
import asyncio
import aiofiles
import json
import logging
import os
from datetime import datetime, timedelta
from openai import OpenAI
import config

# ログ設定
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
log_dir = os.getenv('LOG_DIR', 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'discord_news.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Discord Bot設定
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# OpenAI Client
openai_client = OpenAI(api_key=config.OPENAI_API_KEY)

# 最後に要約した時刻を記録
last_summary_time = {}

class DiscordNewsBot:
    def __init__(self):
        self.message_cache = {}
        
    async def fetch_recent_messages(self, channel, hours_back=None):
        """指定した時間から現在までのメッセージを取得"""
        messages = []
        if hours_back is None:
            hours_back = config.SUMMARY_INTERVAL_HOURS
            
        # 最後の要約時刻から取得、なければ指定時間前から
        if channel.id in last_summary_time:
            after_time = last_summary_time[channel.id]
        else:
            after_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        try:
            async for message in channel.history(
                limit=config.MAX_MESSAGES_PER_CHANNEL,
                after=after_time
            ):
                if not message.author.bot:  # ボットのメッセージは除外
                    messages.append({
                        'author': message.author.display_name,
                        'content': message.content,
                        'timestamp': message.created_at.isoformat(),
                        'attachments': [att.url for att in message.attachments],
                        'replies': len(message.replies) if hasattr(message, 'replies') else 0
                    })
                    
        except Exception as e:
            logger.error(f"メッセージ取得エラー (チャンネル: {channel.name}): {e}")
            
        # 時系列順にソート
        messages.sort(key=lambda x: x['timestamp'])
        return messages
    
    async def generate_summary(self, channel_name, messages, start_time, end_time):
        """GPT APIを使用してメッセージを要約"""
        if not messages:
            return "この期間中に新しいメッセージはありませんでした。"
        
        # メッセージを文字列形式に変換
        messages_text = "\n".join([
            f"[{msg['timestamp']}] {msg['author']}: {msg['content']}"
            for msg in messages
        ])
        
        prompt = config.SUMMARY_PROMPT.format(
            channel_name=channel_name,
            start_time=start_time.strftime("%Y-%m-%d %H:%M:%S"),
            end_time=end_time.strftime("%Y-%m-%d %H:%M:%S"),
            messages=messages_text
        )
        
        try:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "あなたはDiscordの議論内容を要約する専門アシスタントです。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"要約生成エラー: {e}")
            return f"要約の生成中にエラーが発生しました: {str(e)}"
    
    async def save_summary(self, channel_name, summary, messages_count):
        """要約をファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_dir = os.getenv('SUMMARY_DIR', 'summaries')
        os.makedirs(summary_dir, exist_ok=True)
        filename = os.path.join(summary_dir, f"{channel_name}_{timestamp}.json")
        
        summary_data = {
            "channel_name": channel_name,
            "timestamp": timestamp,
            "messages_count": messages_count,
            "summary": summary
        }
        
        try:
            async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(summary_data, ensure_ascii=False, indent=2))
            logger.info(f"要約をファイルに保存: {filename}")
        except Exception as e:
            logger.error(f"ファイル保存エラー: {e}")

    async def post_summary_to_channel(self, summary_channel, channel_name, summary, messages_count):
        """要約を指定チャンネルに投稿"""
        try:
            embed = discord.Embed(
                title=f"📊 {channel_name} チャンネル要約",
                description=summary,
                color=0x00ff00,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="📝 メッセージ数", value=f"{messages_count}件", inline=True)
            embed.add_field(name="⏰ 要約時刻", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=True)
            
            await summary_channel.send(embed=embed)
            logger.info(f"要約を投稿: {channel_name}")
            
        except Exception as e:
            logger.error(f"要約投稿エラー: {e}")

# DiscordNewsBot インスタンス
news_bot = DiscordNewsBot()

@bot.event
async def on_ready():
    logger.info(f'{bot.user} でログインしました')
    
    # チャンネル要約タスクを開始
    if not summary_task.is_running():
        summary_task.start()
    
    logger.info(f"要約タスクを開始しました（{config.SUMMARY_INTERVAL_HOURS}時間間隔）")

@tasks.loop(hours=config.SUMMARY_INTERVAL_HOURS)
async def summary_task():
    """定期的にチャンネルの要約を実行"""
    try:
        guild = bot.get_guild(config.GUILD_ID)
        if not guild:
            logger.error(f"サーバーが見つかりません: {config.GUILD_ID}")
            return
        
        summary_channel = bot.get_channel(config.SUMMARY_CHANNEL_ID)
        if not summary_channel:
            logger.error(f"要約投稿チャンネルが見つかりません: {config.SUMMARY_CHANNEL_ID}")
            return
        
        current_time = datetime.utcnow()
        
        for channel_id in config.CHANNEL_IDS:
            channel = bot.get_channel(channel_id)
            if not channel:
                logger.warning(f"チャンネルが見つかりません: {channel_id}")
                continue
            
            logger.info(f"チャンネル {channel.name} の要約を開始")
            
            # メッセージを取得
            messages = await news_bot.fetch_recent_messages(channel)
            
            if messages:
                start_time = last_summary_time.get(channel.id, current_time - timedelta(hours=config.SUMMARY_INTERVAL_HOURS))
                
                # 要約を生成
                summary = await news_bot.generate_summary(
                    channel.name, messages, start_time, current_time
                )
                
                # ファイルに保存
                await news_bot.save_summary(channel.name, summary, len(messages))
                
                # チャンネルに投稿
                await news_bot.post_summary_to_channel(
                    summary_channel, channel.name, summary, len(messages)
                )
                
                # 最後の要約時刻を更新
                last_summary_time[channel.id] = current_time
            else:
                logger.info(f"チャンネル {channel.name} に新しいメッセージはありません")
        
        logger.info("全チャンネルの要約が完了しました")
        
    except Exception as e:
        logger.error(f"要約タスクエラー: {e}")

@bot.command(name='summary')
async def manual_summary(ctx, channel_id: int = None, hours: int = None):
    """手動で指定チャンネルの要約を実行"""
    if channel_id is None:
        channel = ctx.channel
    else:
        channel = bot.get_channel(channel_id)
        
    if not channel:
        await ctx.send("指定されたチャンネルが見つかりません。")
        return
    
    if hours is None:
        hours = config.SUMMARY_INTERVAL_HOURS
    
    try:
        await ctx.send(f"🔄 {channel.name} の要約を開始しています...")
        
        # メッセージを取得
        messages = await news_bot.fetch_recent_messages(channel, hours)
        
        if not messages:
            await ctx.send("指定された期間に新しいメッセージはありませんでした。")
            return
        
        current_time = datetime.utcnow()
        start_time = current_time - timedelta(hours=hours)
        
        # 要約を生成
        summary = await news_bot.generate_summary(
            channel.name, messages, start_time, current_time
        )
        
        # ファイルに保存
        await news_bot.save_summary(channel.name, summary, len(messages))
        
        # 結果をEmbed形式で投稿
        embed = discord.Embed(
            title=f"📊 {channel.name} チャンネル要約",
            description=summary,
            color=0x00ff00,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="📝 メッセージ数", value=f"{len(messages)}件", inline=True)
        embed.add_field(name="⏰ 対象期間", value=f"過去{hours}時間", inline=True)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        logger.error(f"手動要約エラー: {e}")
        await ctx.send(f"要約の生成中にエラーが発生しました: {str(e)}")

@bot.command(name='status')
async def status(ctx):
    """ボットの状態を確認"""
    embed = discord.Embed(
        title="🤖 Discord News Bot ステータス",
        color=0x0099ff,
        timestamp=datetime.utcnow()
    )
    
    embed.add_field(name="📊 監視中チャンネル数", value=f"{len(config.CHANNEL_IDS)}個", inline=True)
    embed.add_field(name="⏰ 要約間隔", value=f"{config.SUMMARY_INTERVAL_HOURS}時間", inline=True)
    embed.add_field(name="🔄 タスク状況", value="実行中" if summary_task.is_running() else "停止中", inline=True)
    
    # 最後の要約時刻を表示
    if last_summary_time:
        last_times = "\n".join([
            f"<#{channel_id}>: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            for channel_id, time in last_summary_time.items()
        ])
        embed.add_field(name="📅 最後の要約時刻", value=last_times or "まだ要約を実行していません", inline=False)
    
    await ctx.send(embed=embed)

if __name__ == "__main__":
    if not config.DISCORD_BOT_TOKEN:
        logger.error("DISCORD_BOT_TOKEN が設定されていません")
        exit(1)
    
    if not config.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY が設定されていません")
        exit(1)
    
    try:
        bot.run(config.DISCORD_BOT_TOKEN)
    except Exception as e:
        logger.error(f"ボット起動エラー: {e}")
