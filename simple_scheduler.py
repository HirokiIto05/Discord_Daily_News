import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
import openai
import aiofiles
import aiohttp
import config

# OpenAI設定
openai.api_key = config.OPENAI_API_KEY

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

class SimpleDiscordSummarizer:
    """Discord API直接使用による最小構成の要約システム"""
    
    def __init__(self):
        self.last_run_file = "last_run.json"
        self.session = None
        self.headers = {
            "Authorization": f"Bot {config.DISCORD_BOT_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "Discord-News-Summarizer/1.0"
        }
        
    async def get_last_run_times(self):
        """最後の実行時刻を取得"""
        try:
            if os.path.isfile(self.last_run_file):
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
    
    async def resolve_channel_ids(self, session):
        """チャンネル名をチャンネルIDに解決"""
        resolved_ids = []
        
        for channel in config.CHANNEL_IDS:
            if isinstance(channel, int):
                # 既に数値の場合はそのまま使用
                resolved_ids.append(channel)
            else:
                # 文字列の場合は名前からIDを解決
                channel_id = await self.get_channel_id_by_name(session, channel)
                if channel_id:
                    resolved_ids.append(channel_id)
                else:
                    logger.warning(f"チャンネル名 '{channel}' のIDが見つかりませんでした")
        
        return resolved_ids
    
    async def get_channel_id_by_name(self, session, channel_name):
        """チャンネル名からチャンネルIDを取得"""
        if not config.GUILD_ID:
            logger.error("GUILD_IDが設定されていません")
            return None
            
        url = f"https://discord.com/api/v10/guilds/{config.GUILD_ID}/channels"
        try:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    channels = await response.json()
                    for ch in channels:
                        if ch.get('name') == channel_name and ch.get('type') == 0:  # テキストチャンネル
                            logger.info(f"チャンネル名 '{channel_name}' のID: {ch['id']}")
                            return int(ch['id'])
                else:
                    logger.error(f"チャンネル一覧取得失敗: {response.status}")
        except Exception as e:
            logger.error(f"チャンネル名解決エラー: {e}")
        
        return None
    
    async def fetch_channel_info(self, session, channel_id):
        """チャンネル情報を取得"""
        url = f"https://discord.com/api/v10/channels/{channel_id}"
        try:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    channel_data = await response.json()
                    return channel_data.get('name', f'Channel-{channel_id}')
                else:
                    logger.error(f"チャンネル情報取得失敗: {response.status}")
                    return f'Channel-{channel_id}'
        except Exception as e:
            logger.error(f"チャンネル情報取得エラー: {e}")
            return f'Channel-{channel_id}'
    
    async def fetch_messages_since(self, session, channel_id, since_time):
        """指定時刻以降のメッセージを取得"""
        messages = []
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        
        # since_timeをDiscord APIの形式に変換（ISO 8601）
        after_timestamp = since_time.isoformat() + 'Z'
        
        try:
            params = {
                'limit': min(config.MAX_MESSAGES_PER_CHANNEL, 100),  # Discord APIの制限
                'after': int(since_time.timestamp() * 1000)  # Snowflake ID形式
            }
            
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status == 200:
                    message_data = await response.json()
                    
                    for msg in message_data:
                        # ボットメッセージは除外
                        if msg.get('author', {}).get('bot', False):
                            continue
                            
                        # タイムスタンプをパース
                        msg_time = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
                        
                        # since_time以降のメッセージのみ追加
                        if msg_time > since_time:
                            messages.append({
                                'author': msg['author']['username'],
                                'content': msg['content'],
                                'timestamp': msg['timestamp'],
                                'attachments': [att['url'] for att in msg.get('attachments', [])],
                            })
                else:
                    logger.error(f"メッセージ取得失敗: {response.status}")
                    
        except Exception as e:
            logger.error(f"メッセージ取得エラー (チャンネル: {channel_id}): {e}")
        
        # 時系列順にソート
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
            response = openai.ChatCompletion.create(
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
    
    async def save_summary(self, channel_name, summary, messages_count, start_time, end_time, messages):
        """要約とメッセージをファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_dir = os.getenv('SUMMARY_DIR', 'summaries')
        os.makedirs(summary_dir, exist_ok=True)
        
        summary_data = {
            "channel_name": channel_name,
            "summary_timestamp": timestamp,
            "period_start": start_time.isoformat(),
            "period_end": end_time.isoformat(),
            "messages_count": messages_count,
            "summary": summary,
            "raw_messages": messages  # 元メッセージも保存
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
    
    async def run_summary_job(self):
        """要約ジョブを実行（1回のみ）"""
        logger.info("Discord要約ジョブを開始")
        
        async with aiohttp.ClientSession() as session:
            try:
                # チャンネル名をIDに解決
                resolved_channel_ids = await self.resolve_channel_ids(session)
                if not resolved_channel_ids:
                    logger.error("有効なチャンネルIDが見つかりませんでした")
                    return []
                
                logger.info(f"解決されたチャンネルID: {resolved_channel_ids}")
                
                # 最後の実行時刻を取得
                last_run_times = await self.get_last_run_times()
                current_time = datetime.utcnow()
                
                # 各チャンネルを処理
                summaries = []
                for channel_id in resolved_channel_ids:
                    try:
                        # チャンネル名を取得
                        channel_name = await self.fetch_channel_info(session, channel_id)
                        
                        # 最後の実行時刻を取得、なければ設定時間前から
                        if channel_id in last_run_times:
                            since_time = last_run_times[channel_id]
                        else:
                            since_time = current_time - timedelta(hours=config.SUMMARY_INTERVAL_HOURS)
                        
                        # UTCタイムゾーンを追加（比較エラー回避）
                        if since_time.tzinfo is None:
                            since_time = since_time.replace(tzinfo=timezone.utc)
                        
                        logger.info(f"チャンネル {channel_name} の要約を開始 (since: {since_time})")
                        
                        # メッセージを取得
                        messages = await self.fetch_messages_since(session, channel_id, since_time)
                        
                        if messages:
                            # 要約を生成
                            summary = await self.generate_summary(
                                channel_name, messages, since_time, current_time
                            )
                            
                            # ファイルに保存
                            filename = await self.save_summary(
                                channel_name, summary, len(messages), since_time, current_time, messages
                            )
                            
                            summaries.append({
                                'channel_name': channel_name,
                                'channel_id': channel_id,
                                'messages_count': len(messages),
                                'summary': summary,
                                'filename': filename
                            })
                            
                            # 最後の実行時刻を更新
                            last_run_times[channel_id] = current_time
                        else:
                            logger.info(f"チャンネル {channel_name} に新しいメッセージはありません")
                    
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

async def main():
    """メイン実行関数"""
    if not config.DISCORD_BOT_TOKEN:
        logger.error("DISCORD_BOT_TOKEN が設定されていません")
        exit(1)
    
    if not config.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY が設定されていません")
        exit(1)
    
    summarizer = SimpleDiscordSummarizer()
    summaries = await summarizer.run_summary_job()
    
    print(f"\n🎉 要約完了: {len(summaries)}件")
    print("📁 要約ファイルは summaries/ ディレクトリに保存されました")
    
    # 要約一覧を表示
    if summaries:
        print("\n📊 生成された要約:")
        for summary in summaries:
            print(f"  - {summary['channel_name']}: {summary['messages_count']}件")
            print(f"    ファイル: {summary['filename']}")
    
    return summaries

if __name__ == "__main__":
    asyncio.run(main())
