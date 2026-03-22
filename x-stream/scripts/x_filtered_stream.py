#!/usr/bin/env python3
"""
X API Filtered Stream Client for OpenClaw
Monitors tweets in real-time using X's Filtered Stream API
Sends notifications to Discord via webhook

Requires: Bearer Token (App-only authentication)
Get it from: X Developer Portal -> Your App -> Keys and tokens -> Bearer Token
"""

import json
import os
import urllib.request
import urllib.parse
import urllib.error
import ssl
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

# Configuration paths
# Determine workspace root (works both in OpenClaw and standalone)
SCRIPT_DIR = Path(__file__).parent
WORKSPACE_ROOT = SCRIPT_DIR.parent.parent.parent  # skills/x-stream/scripts -> workspace
DATA_DIR = WORKSPACE_ROOT / "data" / "x"
STREAM_CONFIG_FILE = DATA_DIR / "x-stream-config.json"
BEARER_TOKEN_FILE = DATA_DIR / "x-bearer-token.json"
STATE_FILE = DATA_DIR / "x-stream-state.json"
WEBHOOK_FILE = DATA_DIR / "x-discord-webhook.json"


class DiscordNotifier:
    """Discord Webhook通知クラス"""
    
    def __init__(self):
        self.webhook_url = None
        self._load_webhook()
    
    def _load_webhook(self):
        """Webhook URLをファイルから読み込み"""
        if WEBHOOK_FILE.exists():
            with open(WEBHOOK_FILE, 'r') as f:
                data = json.load(f)
                self.webhook_url = data.get('webhook_url')
    
    def send_tweet_notification(self, tweet_data, username=None, avatar_url=None):
        """ツイート通知をDiscordに送信"""
        if not self.webhook_url:
            print("⚠️ Discord Webhook URL not configured")
            return False
        
        if 'data' not in tweet_data:
            return False
        
        tweet = tweet_data['data']
        tweet_id = tweet.get('id')
        tweet_text = tweet.get('text', '')
        created_at = tweet.get('created_at', '')
        author_id = tweet.get('author_id', '')
        
        # ツイートURL
        tweet_url = f"https://x.com/i/web/status/{tweet_id}"
        
        # メトリクス
        metrics = tweet.get('public_metrics', {})
        likes = metrics.get('like_count', 0)
        retweets = metrics.get('retweet_count', 0)
        replies = metrics.get('reply_count', 0)
        
        # Discord Embed作成
        embed = {
            "title": "🐦 新規ツイート検知",
            "description": tweet_text[:2000] if len(tweet_text) > 2000 else tweet_text,
            "url": tweet_url,
            "color": 0x1DA1F2,  # X Blue
            "fields": [
                {
                    "name": "📊 メトリクス",
                    "value": f"❤️ {likes}  🔄 {retweets}  💬 {replies}",
                    "inline": True
                },
                {
                    "name": "🆔 ツイートID",
                    "value": tweet_id,
                    "inline": True
                }
            ],
            "timestamp": created_at,
            "footer": {
                "text": f"Author ID: {author_id}"
            }
        }
        
        # エージェントにメンションしてタスク依頼
        agent_mention = "<@1475431819565469706>"
        task_instruction = """x-quote-explain skillを使って引用リツイート解説してください。

**解説作成の手順:**
1. x-read skillでツイート詳細を取得
2. ツイートの内容を分析
3. Web検索で関連情報を収集
4. x-quote-explainスキルで引用リツイート投稿

**解説の要件:**
- 文字数制限なし（課金ユーザー）
- 1文は短めに（読みやすさ重視）
- 具体例や数値を含める
- 公式情報源を参照
- 初心者にもわかりやすく"""
        
        payload = {
            "username": username or "X Stream Monitor",
            "avatar_url": avatar_url or "https://abs.twimg.com/icons/apple-touch-icon-192x192.png",
            "embeds": [embed],
            "content": f"{agent_mention} {task_instruction}\n\n🔗 ツイートURL: {tweet_url}"
        }
        
        try:
            body = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                self.webhook_url,
                data=body,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'OpenClaw-X-Stream/1.0'
                },
                method='POST'
            )
            
            with urllib.request.urlopen(req) as resp:
                if resp.status in [200, 204]:
                    print(f"✅ Discord通知送信完了: {tweet_id}")
                    return True
                else:
                    print(f"⚠️ Discord通知失敗: {resp.status}")
                    return False
                    
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else "No details"
            print(f"❌ Discord Webhook Error: {e.code} - {error_body}")
            return False
        except Exception as e:
            print(f"❌ Discord通知エラー: {e}")
            return False

class XFilteredStreamClient:
    def __init__(self):
        self.bearer_token = None
        self.config = None
        self.running = True
        self.discord = DiscordNotifier()
        self._load_bearer_token()
        self._load_config()
        self._setup_signal_handlers()
    
    def _load_bearer_token(self):
        """Load Bearer Token from file"""
        if BEARER_TOKEN_FILE.exists():
            with open(BEARER_TOKEN_FILE, 'r') as f:
                data = json.load(f)
                self.bearer_token = data.get('bearer_token')
        else:
            # Try environment variable
            self.bearer_token = os.environ.get('X_BEARER_TOKEN')
    
    def _load_config(self):
        """Load stream configuration"""
        if STREAM_CONFIG_FILE.exists():
            with open(STREAM_CONFIG_FILE, 'r') as f:
                self.config = json.load(f)
        else:
            # Default config
            self.config = {
                "rules": [
                    {
                        "value": "from:hAru_mAki_ch -is:retweet -is:reply",
                        "tag": "haru_maki_new_posts"
                    }
                ],
                "tweet_fields": ["created_at", "author_id", "public_metrics", "entities"],
                "on_tweet_callback": None
            }
    
    def _save_state(self, state):
        """Save stream state"""
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _setup_signal_handlers(self):
        """Handle graceful shutdown"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        print("\n🛑 Stopping stream...")
        self.running = False
        sys.exit(0)
    
    def _api_request(self, endpoint, method="GET", data=None, stream=False):
        """Make API request to X API v2"""
        if not self.bearer_token:
            raise Exception("Bearer Token not configured. Set X_BEARER_TOKEN env or create x-bearer-token.json")
        
        url = f"https://api.x.com{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.bearer_token}',
            'Content-Type': 'application/json'
        }
        
        body = json.dumps(data).encode() if data else None
        
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        
        if stream:
            return urllib.request.urlopen(req)
        else:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode())
    
    # === Rule Management ===
    
    def list_rules(self):
        """List current stream rules"""
        try:
            result = self._api_request('/2/tweets/search/stream/rules')
            return result
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"data": [], "meta": {"sent": datetime.now(timezone.utc).isoformat()}}
            raise
    
    def add_rule(self, value, tag=None):
        """Add a stream rule"""
        rule = {"value": value}
        if tag:
            rule["tag"] = tag
        
        data = {"add": [rule]}
        return self._api_request('/2/tweets/search/stream/rules', method="POST", data=data)
    
    def add_rules(self, rules):
        """Add multiple stream rules
        
        Args:
            rules: List of dicts with 'value' and optional 'tag'
                   e.g., [{"value": "from:user -is:retweet", "tag": "user_posts"}]
        """
        data = {"add": rules}
        return self._api_request('/2/tweets/search/stream/rules', method="POST", data=data)
    
    def delete_rule(self, rule_ids):
        """Delete stream rules by ID"""
        if isinstance(rule_ids, str):
            rule_ids = [rule_ids]
        data = {"delete": {"ids": rule_ids}}
        return self._api_request('/2/tweets/search/stream/rules', method="POST", data=data)
    
    def clear_rules(self):
        """Delete all rules"""
        rules = self.list_rules()
        if 'data' in rules and rules['data']:
            ids = [r['id'] for r in rules['data']]
            return self.delete_rule(ids)
        return {"message": "No rules to delete"}
    
    # === Stream Connection ===
    
    def connect_stream(self, on_tweet=None, tweet_fields=None):
        """Connect to filtered stream and process tweets
        
        Args:
            on_tweet: Callback function(tweet_data) called for each tweet
            tweet_fields: List of tweet fields to include
        """
        if not self.bearer_token:
            raise Exception("Bearer Token not configured")
        
        # Build URL with parameters
        params = {}
        if tweet_fields:
            params['tweet.fields'] = ','.join(tweet_fields)
        elif self.config.get('tweet_fields'):
            params['tweet.fields'] = ','.join(self.config['tweet_fields'])
        
        # Default fields
        if 'tweet.fields' not in params:
            params['tweet.fields'] = 'created_at,author_id,public_metrics,entities'
        
        url = f"https://api.x.com/2/tweets/search/stream?{urllib.parse.urlencode(params)}"
        
        headers = {
            'Authorization': f'Bearer {self.bearer_token}'
        }
        
        req = urllib.request.Request(url, headers=headers)
        
        print(f"🔌 Connecting to filtered stream...")
        print(f"📋 Active rules: {len(self.config.get('rules', []))}")
        
        try:
            with urllib.request.urlopen(req) as resp:
                print("✅ Connected! Listening for tweets...\n")
                
                buffer = ""
                for line in resp:
                    if not self.running:
                        break
                    
                    line = line.decode('utf-8').strip()
                    
                    if not line:
                        # Empty line signals end of tweet
                        if buffer:
                            try:
                                tweet_data = json.loads(buffer)
                                
                                # Save state
                                self._save_state({
                                    "last_tweet_at": datetime.now(timezone.utc).isoformat(),
                                    "last_tweet_id": tweet_data.get('data', {}).get('id')
                                })
                                
                                # Process tweet
                                if on_tweet:
                                    on_tweet(tweet_data)
                                else:
                                    self._default_tweet_handler(tweet_data)
                                    
                            except json.JSONDecodeError as e:
                                print(f"⚠️ JSON decode error: {e}")
                            buffer = ""
                    else:
                        buffer += line
                        
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else "No error details"
            print(f"❌ HTTP Error {e.code}: {error_body}")
            raise
        except Exception as e:
            print(f"❌ Stream error: {e}")
            raise
    
    def _default_tweet_handler(self, tweet_data):
        """Default handler for incoming tweets"""
        if 'data' in tweet_data:
            tweet = tweet_data['data']
            print(f"\n{'='*60}")
            print(f"📝 New Tweet at {tweet.get('created_at', 'N/A')}")
            print(f"🆔 ID: {tweet.get('id')}")
            print(f"👤 Author ID: {tweet.get('author_id')}")
            print(f"\n💬 {tweet.get('text', '')}")
            
            if 'public_metrics' in tweet:
                metrics = tweet['public_metrics']
                print(f"\n📊 Metrics: ❤️ {metrics.get('like_count', 0)} 🔄 {metrics.get('retweet_count', 0)} 💬 {metrics.get('reply_count', 0)}")
            
            print(f"{'='*60}\n")
            
            # Discordに通知
            self.discord.send_tweet_notification(tweet_data)
        
        elif 'errors' in tweet_data:
            print(f"⚠️ Errors: {tweet_data['errors']}")
    
    # === Convenience Methods ===
    
    def setup_default_rules(self):
        """Setup default rules for monitoring hAru_mAki_ch"""
        rules = self.config.get('rules', [
            {"value": "from:hAru_mAki_ch -is:retweet -is:reply", "tag": "haru_maki_new_posts"}
        ])
        
        # Clear existing rules first
        print("🧹 Clearing existing rules...")
        try:
            self.clear_rules()
        except:
            pass
        
        # Add new rules
        print(f"➕ Adding {len(rules)} rules...")
        result = self.add_rules(rules)
        print(f"✅ Rules added: {json.dumps(result, indent=2)}")
        return result


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("X API Filtered Stream Client")
        print("\nUsage: python x_filtered_stream.py <command> [args...]")
        print("\nCommands:")
        print("  rules              - List current stream rules")
        print("  setup              - Setup default rules (hAru_mAki_ch)")
        print("  add <value> [tag]  - Add a new rule")
        print("  clear              - Delete all rules")
        print("  stream             - Connect to stream and listen")
        print("  test               - Test connection and list rules")
        print("  webhook <url>      - Set Discord webhook URL")
        print("  test-webhook       - Test Discord webhook")
        print("\nEnvironment:")
        print("  X_BEARER_TOKEN     - Bearer Token (or create x-bearer-token.json)")
        print("\nExample:")
        print("  export X_BEARER_TOKEN='your_token_here'")
        print("  python x_filtered_stream.py webhook 'https://discord.com/api/webhooks/...'")
        print("  python x_filtered_stream.py setup")
        print("  python x_filtered_stream.py stream")
        sys.exit(1)
    
    client = XFilteredStreamClient()
    command = sys.argv[1]
    
    try:
        if command == "rules":
            result = client.list_rules()
            print(json.dumps(result, indent=2))
        
        elif command == "setup":
            result = client.setup_default_rules()
            print(json.dumps(result, indent=2))
        
        elif command == "add":
            if len(sys.argv) < 3:
                print("Usage: python x_filtered_stream.py add <rule_value> [tag]")
                sys.exit(1)
            value = sys.argv[2]
            tag = sys.argv[3] if len(sys.argv) > 3 else None
            result = client.add_rule(value, tag)
            print(json.dumps(result, indent=2))
        
        elif command == "clear":
            result = client.clear_rules()
            print(json.dumps(result, indent=2))
        
        elif command == "webhook":
            if len(sys.argv) < 3:
                print("Usage: python x_filtered_stream.py webhook <webhook_url>")
                print("\nCurrent webhook:", client.discord.webhook_url or "Not set")
                sys.exit(1)
            
            webhook_url = sys.argv[2]
            WEBHOOK_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(WEBHOOK_FILE, 'w') as f:
                json.dump({"webhook_url": webhook_url}, f, indent=2)
            print(f"✅ Discord Webhook URL saved to: {WEBHOOK_FILE}")
        
        elif command == "test-webhook":
            if not client.discord.webhook_url:
                print("❌ Webhook URL not configured")
                print("Usage: python x_filtered_stream.py webhook <url>")
                sys.exit(1)
            
            # テスト用ダミーツイート（実際のhAru_mAki_chのツイート）
            test_tweet = {
                "data": {
                    "id": "2026299224833597833",
                    "text": "🧪 これはテスト通知です。Filtered Streamが正常に動作していれば、この形式で通知されます。",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "author_id": "hAru_mAki_ch",
                    "public_metrics": {
                        "like_count": 0,
                        "retweet_count": 0,
                        "reply_count": 0
                    }
                }
            }
            
            print("🧪 Testing Discord webhook...")
            success = client.discord.send_tweet_notification(test_tweet)
            if success:
                print("✅ Test notification sent successfully!")
            else:
                print("❌ Test notification failed")
        
        elif command == "stream":
            # Check if bearer token exists
            if not client.bearer_token:
                print("❌ Bearer Token not configured!")
                print("\nCreate file: data/x/x-bearer-token.json")
                print('{\n  "bearer_token": "YOUR_BEARER_TOKEN_HERE"\n}')
                print("\nOr set environment variable: X_BEARER_TOKEN")
                sys.exit(1)
            
            # Check Discord webhook
            if client.discord.webhook_url:
                print(f"✅ Discord Webhook: Configured")
            else:
                print("⚠️ Discord Webhook: Not configured (notifications disabled)")
            
            # Setup rules first
            client.setup_default_rules()
            
            # Start streaming
            client.connect_stream()
        
        elif command == "test":
            print("🔍 Testing configuration...\n")
            print(f"Bearer Token: {'✅ Set' if client.bearer_token else '❌ Not set'}")
            print(f"Discord Webhook: {'✅ Set' if client.discord.webhook_url else '❌ Not set'}")
            print(f"Config file: {'✅ Found' if STREAM_CONFIG_FILE.exists() else '⚠️ Using defaults'}")
            print()
            
            if client.bearer_token:
                print("📋 Current rules:")
                result = client.list_rules()
                print(json.dumps(result, indent=2))
            else:
                print("⚠️ Cannot test API without Bearer Token")
        
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
