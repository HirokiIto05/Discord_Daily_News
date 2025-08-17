import discord
import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from openai import OpenAI
import aiofiles
import config

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('discord_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DiscordScheduler:
    """間欠実行用のDiscord要約スケジューラー"""
    
    def __init__(self):
        self.client = discord.Client(intents=discord.Intents.default())
        self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.last_run_file = "last_run.json"
        
    async def get_last_run_times(self):
        """最後の実行時刻を取得"""
        try:
            if os.path.exists(self.last_run_file):
                async with aiofiles.open(self.last_run_file, 'r') as f:
                    data = json.loads(await f.read())
                    return {int(k): datetime.fromisoformat(v) for k, v in data.items()}
        except Exception as e:
            logger.error(f"最終実行時刻の読み込みエラー: {e}")
        return {}
    
    async def save_last_run_times(self, run_times):
        """最後の実行時刻を保存"""
        try:
            data = {str(k): v.isoformat() for k, v in run_times.items()}
            async with aiofiles.open(self.last_run_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"最終実行時刻の保存エラー: {e}")
    
    async def fetch_messages_since(self, channel, since_time):
        """指定時刻以降のメッセージを取得"""
        messages = []
        try:
            async for message in channel.history(
                limit=config.MAX_MESSAGES_PER_CHANNEL,
                after=since_time
            ):
                if not message.author.bot:
                    messages.append({
                        'author': message.author.display_name,
                        'content': message.content,
                        'timestamp': message.created_at.isoformat(),
                        'attachments': [att.url for att in message.attachments],
                    })
        except Exception as e:
            logger.error(f"メッセージ取得エラー (チャンネル: {channel.name}): {e}")
        
        return sorted(messages, key=lambda x: x['timestamp'])
    
    async def generate_summary(self, channel_name, messages, start_time, end_time):
        """GPT APIを使用してメッセージを要約"""
        if not messages:
            return "この期間中に新しいメッセージはありませんでした。"
        
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
            response = self.openai_client.chat.completions.create(
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
    
    async def save_summary(self, channel_name, summary, messages_count, start_time, end_time):
        """要約をファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_dir = os.getenv('SUMMARY_DIR', 'summaries')
        os.makedirs(summary_dir, exist_ok=True)
        
        summary_data = {
            "channel_name": channel_name,
            "summary_timestamp": timestamp,
            "period_start": start_time.isoformat(),
            "period_end": end_time.isoformat(),
            "messages_count": messages_count,
            "summary": summary
        }
        
        filename = os.path.join(summary_dir, f"{channel_name}_{timestamp}.json")
        try:
            async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(summary_data, ensure_ascii=False, indent=2))
            logger.info(f"要約をファイルに保存: {filename}")
            return filename
        except Exception as e:
            logger.error(f"ファイル保存エラー: {e}")
            return None
    
    async def post_summary_webhook(self, webhook_url, channel_name, summary, messages_count):
        """Webhookを使用して要約を投稿"""
        if not webhook_url:
            return
            
        import aiohttp
        
        embed = {
            "title": f"📊 {channel_name} チャンネル要約",
            "description": summary,
            "color": 0x00ff00,
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [
                {"name": "📝 メッセージ数", "value": f"{messages_count}件", "inline": True},
                {"name": "⏰ 要約時刻", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "inline": True}
            ]
        }
        
        payload = {"embeds": [embed]}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 204:
                        logger.info(f"Webhook投稿成功: {channel_name}")
                    else:
                        logger.error(f"Webhook投稿失敗: {response.status}")
        except Exception as e:
            logger.error(f"Webhook投稿エラー: {e}")
    
    async def run_summary_job(self):
        """要約ジョブを実行（1回のみ）"""
        logger.info("Discord要約ジョブを開始")
        
        try:
            await self.client.login(config.DISCORD_BOT_TOKEN)
            
            # 最後の実行時刻を取得
            last_run_times = await self.get_last_run_times()
            current_time = datetime.utcnow()
            
            # 各チャンネルを処理
            summaries = []
            for channel_id in config.CHANNEL_IDS:
                try:
                    channel = await self.client.fetch_channel(channel_id)
                    if not channel:
                        logger.warning(f"チャンネルが見つかりません: {channel_id}")
                        continue
                    
                    # 最後の実行時刻を取得、なければ設定時間前から
                    if channel_id in last_run_times:
                        since_time = last_run_times[channel_id]
                    else:
                        since_time = current_time - timedelta(hours=config.SUMMARY_INTERVAL_HOURS)
                    
                    logger.info(f"チャンネル {channel.name} の要約を開始 (since: {since_time})")
                    
                    # メッセージを取得
                    messages = await self.fetch_messages_since(channel, since_time)
                    
                    if messages:
                        # 要約を生成
                        summary = await self.generate_summary(
                            channel.name, messages, since_time, current_time
                        )
                        
                        # ファイルに保存
                        filename = await self.save_summary(
                            channel.name, summary, len(messages), since_time, current_time
                        )
                        
                        summaries.append({
                            'channel_name': channel.name,
                            'messages_count': len(messages),
                            'summary': summary,
                            'filename': filename
                        })
                        
                        # Webhook投稿（設定されている場合）
                        webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
                        if webhook_url:
                            await self.post_summary_webhook(
                                webhook_url, channel.name, summary, len(messages)
                            )
                        
                        # 最後の実行時刻を更新
                        last_run_times[channel_id] = current_time
                    else:
                        logger.info(f"チャンネル {channel.name} に新しいメッセージはありません")
                
                except Exception as e:
                    logger.error(f"チャンネル {channel_id} の処理エラー: {e}")
            
            # 最後の実行時刻を保存
            await self.save_last_run_times(last_run_times)
            
            logger.info(f"要約ジョブ完了: {len(summaries)}件の要約を生成")
            
            # 結果サマリーを出力
            for summary in summaries:
                print(f"✅ {summary['channel_name']}: {summary['messages_count']}件のメッセージを要約")
            
            return summaries
            
        except Exception as e:
            logger.error(f"要約ジョブエラー: {e}")
            return []
        finally:
            await self.client.close()

async def main():
    """メイン実行関数"""
    if not config.DISCORD_BOT_TOKEN:
        logger.error("DISCORD_BOT_TOKEN が設定されていません")
        exit(1)
    
    if not config.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY が設定されていません")
        exit(1)
    
    scheduler = DiscordScheduler()
    summaries = await scheduler.run_summary_job()
    
    print(f"\n🎉 要約完了: {len(summaries)}件")
    print("📁 要約ファイルは summaries/ ディレクトリに保存されました")
    
    return summaries

if __name__ == "__main__":
    asyncio.run(main())
