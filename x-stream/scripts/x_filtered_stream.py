#!/usr/bin/env python3
"""
X Filtered Stream Client
X（Twitter）のFiltered Stream APIを使って、リアルタイムにツイートを監視・通知するスクリプト
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
import requests

# 設定ファイルパス
WORKSPACE = Path(__file__).parent.parent.parent.parent
DATA_DIR = WORKSPACE / "data" / "x"
BEARER_TOKEN_FILE = DATA_DIR / "x-bearer-token.json"
WEBHOOK_FILE = DATA_DIR / "x-discord-webhook.json"
STATE_FILE = DATA_DIR / "x-stream-state.json"
CONFIG_FILE = DATA_DIR / "x-stream-config.json"

# X API v2 エンドポイント
BASE_URL = "https://api.twitter.com/2"
RULES_URL = f"{BASE_URL}/tweets/search/stream/rules"
STREAM_URL = f"{BASE_URL}/tweets/search/stream"

# デフォルト設定
DEFAULT_RULES = [
    {
        "value": "from:hAru_mAki_ch -is:retweet -is:reply",
        "tag": "haru_maki_new_posts"
    }
]

DEFAULT_TWEET_FIELDS = [
    "created_at",
    "author_id",
    "public_metrics",
    "entities",
    "attachments"
]

STREAM_RETRY_BASE_SECONDS = 30
STREAM_RETRY_MAX_SECONDS = 300


def load_bearer_token() -> str:
    """Bearer Tokenを読み込み"""
    # 環境変数を優先
    token = os.environ.get("X_BEARER_TOKEN")
    if token:
        return token

    # ファイルから読み込み
    if BEARER_TOKEN_FILE.exists():
        with open(BEARER_TOKEN_FILE) as f:
            data = json.load(f)
            return data.get("bearer_token", "")

    raise ValueError("Bearer Token not found. Set X_BEARER_TOKEN or create data/x/x-bearer-token.json")


def load_webhook_url() -> str | None:
    """Discord Webhook URLを読み込み"""
    if WEBHOOK_FILE.exists():
        with open(WEBHOOK_FILE) as f:
            data = json.load(f)
            return data.get("webhook_url")
    return None


def load_state() -> dict:
    """状態ファイルを読み込み"""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    """状態ファイルを保存"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_config() -> dict:
    """設定ファイルを読み込み"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {
        "rules": DEFAULT_RULES,
        "tweet_fields": DEFAULT_TWEET_FIELDS
    }


def get_headers(token: str) -> dict:
    """APIリクエスト用ヘッダー"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def get_rules(token: str) -> dict:
    """現在のルールを取得"""
    resp = requests.get(RULES_URL, headers=get_headers(token))
    if resp.status_code == 200:
        return resp.json()
    elif resp.status_code == 403:
        print(f"❌ 403 Forbidden - Check your app permissions")
        return {"data": [], "meta": {"result_count": 0}}
    else:
        print(f"❌ Error getting rules: {resp.status_code}")
        print(resp.text)
        return {"data": [], "meta": {"result_count": 0}}


def add_rules(token: str, rules: list) -> bool:
    """ルールを追加"""
    payload = {"add": rules}
    resp = requests.post(RULES_URL, headers=get_headers(token), json=payload)

    if resp.status_code == 200:
        result = resp.json()
        if "errors" in result:
            print(f"⚠️ Some rules had errors: {result['errors']}")
            return False
        print(f"✅ Added {len(rules)} rule(s)")
        return True
    else:
        print(f"❌ Error adding rules: {resp.status_code}")
        print(resp.text)
        return False


def delete_all_rules(token: str) -> bool:
    """全ルールを削除"""
    rules = get_rules(token)
    if not rules.get("data"):
        print("ℹ️ No rules to delete")
        return True

    rule_ids = [r["id"] for r in rules["data"]]
    payload = {"delete": {"ids": rule_ids}}
    resp = requests.post(RULES_URL, headers=get_headers(token), json=payload)

    if resp.status_code == 200:
        print(f"✅ Deleted {len(rule_ids)} rule(s)")
        return True
    else:
        print(f"❌ Error deleting rules: {resp.status_code}")
        print(resp.text)
        return False


def send_discord_notification(tweet: dict, webhook_url: str):
    """Discordに通知を送信"""
    tweet_id = tweet.get("id", "")
    text = tweet.get("text", "")
    author_id = tweet.get("author_id", "")
    created_at = tweet.get("created_at", "")

    # ツイートURL
    tweet_url = f"https://twitter.com/i/web/status/{tweet_id}"

    # Embedメッセージ作成
    embed = {
        "title": "🐦 新規ツイート検知",
        "description": text[:500] + ("..." if len(text) > 500 else ""),
        "url": tweet_url,
        "color": 0x1DA1F2,  # Twitter Blue
        "fields": [
            {"name": "Tweet ID", "value": tweet_id, "inline": True},
            {"name": "Author ID", "value": author_id, "inline": True},
        ],
        "timestamp": created_at,
        "footer": {"text": "X Filtered Stream"}
    }

    # メトリクスがあれば追加
    metrics = tweet.get("public_metrics", {})
    if metrics:
        metrics_text = f"❤️ {metrics.get('like_count', 0)} | 🔄 {metrics.get('retweet_count', 0)} | 💬 {metrics.get('reply_count', 0)}"
        embed["fields"].append({"name": "Metrics", "value": metrics_text, "inline": False})

    payload = {
        "username": "X Stream Monitor",
        "avatar_url": "https://abs.twimg.com/icons/apple-touch-icon-192x192.png",
        "embeds": [embed],
        "content": "<@&1475432244725288973> 新規ツイートを検知しました。解説タスクを実行してください。"
    }

    try:
        resp = requests.post(webhook_url, json=payload)
        if resp.status_code == 204:
            print(f"✅ Discord notification sent for tweet {tweet_id}")
        else:
            print(f"⚠️ Discord notification failed: {resp.status_code}")
    except Exception as e:
        print(f"❌ Error sending Discord notification: {e}")


def test_webhook():
    """Webhook通知テスト"""
    webhook_url = load_webhook_url()
    if not webhook_url:
        print("❌ No webhook URL configured")
        return False

    test_tweet = {
        "id": "test123",
        "text": "これはテスト通知です",
        "author_id": "test_user",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "public_metrics": {"like_count": 0, "retweet_count": 0, "reply_count": 0}
    }

    send_discord_notification(test_tweet, webhook_url)
    return True


def stream_tweets(token: str):
    """ストリームを開始"""
    config = load_config()
    tweet_fields = ",".join(config.get("tweet_fields", DEFAULT_TWEET_FIELDS))
    stream_url = f"{STREAM_URL}?tweet_fields={tweet_fields}"

    print(f"🔊 Starting filtered stream...")
    print(f"📡 Connecting to: {stream_url}")

    webhook_url = load_webhook_url()
    retry_delay = STREAM_RETRY_BASE_SECONDS

    while True:
        try:
            with requests.get(stream_url, headers=get_headers(token), stream=True, timeout=(10, 90)) as resp:
                if resp.status_code == 429:
                    print(f"⚠️ Stream rate limited. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, STREAM_RETRY_MAX_SECONDS)
                    continue

                if resp.status_code != 200:
                    print(f"❌ Stream connection failed: {resp.status_code}")
                    print(resp.text)
                    print(f"⏳ Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, STREAM_RETRY_MAX_SECONDS)
                    continue

                retry_delay = STREAM_RETRY_BASE_SECONDS
                print("✅ Stream connected. Listening for tweets...")
                print("Press Ctrl+C to stop\n")

                for line in resp.iter_lines():
                    if not line:
                        continue

                    try:
                        data = json.loads(line)

                        # Keep-alive信号をスキップ
                        if not data:
                            continue

                        # エラーチェック
                        if "errors" in data:
                            print(f"⚠️ Stream error: {data['errors']}")
                            continue

                        # ツイートデータ処理
                        if "data" in data:
                            tweet = data["data"]
                            tweet_id = tweet.get("id")
                            text = tweet.get("text", "")[:100]

                            print(f"\n🐦 Tweet: {tweet_id}")
                            print(f"   {text}...")

                            # 状態を保存
                            state = load_state()
                            state["last_tweet_id"] = tweet_id
                            state["last_tweet_at"] = datetime.now(timezone.utc).isoformat()
                            save_state(state)

                            # Discord通知
                            if webhook_url:
                                send_discord_notification(tweet, webhook_url)

                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"⚠️ Error processing tweet: {e}")
                        continue

                print(f"⚠️ Stream disconnected. Reconnecting in {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, STREAM_RETRY_MAX_SECONDS)

        except KeyboardInterrupt:
            print("\n\n👋 Stream stopped by user")
            return
        except Exception as e:
            print(f"❌ Stream error: {e}")
            print(f"⏳ Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, STREAM_RETRY_MAX_SECONDS)


def cmd_test(args):
    """設定確認テスト"""
    print("🔧 Testing X Filtered Stream configuration...\n")

    # Bearer Token
    try:
        token = load_bearer_token()
        print(f"✅ Bearer Token: {token[:20]}...")
    except ValueError as e:
        print(f"❌ {e}")
        return 1

    # API接続テスト
    print("\n📡 Testing API connection...")
    rules = get_rules(token)
    count = rules.get("meta", {}).get("result_count", 0)
    print(f"✅ API connection OK. Current rules: {count}")

    # Webhook
    webhook_url = load_webhook_url()
    if webhook_url:
        print(f"✅ Discord Webhook: {webhook_url[:50]}...")
    else:
        print("⚠️ No Discord webhook configured")

    # 状態
    state = load_state()
    if state:
        print(f"\n📊 Last state:")
        print(f"   Last tweet ID: {state.get('last_tweet_id', 'N/A')}")
        print(f"   Last tweet at: {state.get('last_tweet_at', 'N/A')}")

    print("\n✅ All checks passed!")
    return 0


def cmd_setup(args):
    """デフォルトルールを設定"""
    token = load_bearer_token()
    config = load_config()
    rules = config.get("rules", DEFAULT_RULES)

    print(f"🔧 Setting up {len(rules)} default rule(s)...")

    # 既存ルールを削除
    delete_all_rules(token)

    # 新規ルールを追加
    if add_rules(token, rules):
        print("\n✅ Setup complete!")
        print("\nCurrent rules:")
        cmd_rules(args)
    return 0


def cmd_add(args):
    """カスタムルールを追加"""
    token = load_bearer_token()

    rule = {"value": args.value}
    if args.tag:
        rule["tag"] = args.tag

    if add_rules(token, [rule]):
        print("\n✅ Rule added!")
    return 0


def cmd_rules(args):
    """現在のルールを表示"""
    token = load_bearer_token()
    rules = get_rules(token)

    data = rules.get("data", [])
    if not data:
        print("ℹ️ No rules configured")
        return 0

    print(f"📋 Current rules ({len(data)}):\n")
    for i, rule in enumerate(data, 1):
        tag = rule.get("tag", "N/A")
        value = rule.get("value", "")
        print(f"  {i}. [{tag}] {value}")

    return 0


def cmd_clear(args):
    """全ルールを削除"""
    token = load_bearer_token()
    delete_all_rules(token)
    return 0


def cmd_stream(args):
    """ストリームを開始"""
    token = load_bearer_token()

    # ルール確認
    rules = get_rules(token)
    if not rules.get("data"):
        print("⚠️ No rules configured. Run 'setup' first.")
        return 1

    print(f"📋 Active rules: {len(rules['data'])}")
    stream_tweets(token)
    return 0


def cmd_test_webhook(args):
    """Webhook通知テスト"""
    print("🔔 Testing Discord webhook notification...\n")
    if test_webhook():
        print("\n✅ Test notification sent!")
        return 0
    return 1


def main():
    parser = argparse.ArgumentParser(
        description="X Filtered Stream Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  test          Test configuration and API connection
  setup         Set up default rules
  add           Add a custom rule
  rules         Show current rules
  clear         Delete all rules
  stream        Start streaming tweets
  test-webhook  Test Discord webhook notification

Examples:
  %(prog)s test
  %(prog)s setup
  %(prog)s add "from:username -is:retweet" "my_tag"
  %(prog)s stream
"""
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # test
    subparsers.add_parser("test", help="Test configuration")

    # setup
    subparsers.add_parser("setup", help="Set up default rules")

    # add
    add_parser = subparsers.add_parser("add", help="Add a custom rule")
    add_parser.add_argument("value", help="Rule value (e.g., 'from:user -is:retweet')")
    add_parser.add_argument("tag", nargs="?", help="Rule tag")

    # rules
    subparsers.add_parser("rules", help="Show current rules")

    # clear
    subparsers.add_parser("clear", help="Delete all rules")

    # stream
    stream_parser = subparsers.add_parser("stream", help="Start streaming tweets")
    stream_parser.add_argument(
        "--auto-quote",
        action="store_true",
        help="Legacy compatibility flag. Currently ignored.",
    )

    # test-webhook
    subparsers.add_parser("test-webhook", help="Test Discord webhook")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "test": cmd_test,
        "setup": cmd_setup,
        "add": cmd_add,
        "rules": cmd_rules,
        "clear": cmd_clear,
        "stream": cmd_stream,
        "test-webhook": cmd_test_webhook,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
