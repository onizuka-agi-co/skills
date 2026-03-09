#!/usr/bin/env python3
"""
X Filtered Stream Client
リアルタイムにツイートを監視・通知するスクリプト
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import requests

# 設定ファイルのパス
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
BEARER_TOKEN_FILE = WORKSPACE_ROOT / "data" / "x" / "x-bearer-token.json"
WEBHOOK_FILE = WORKSPACE_ROOT / "data" / "x" / "x-discord-webhook.json"
STATE_FILE = WORKSPACE_ROOT / "data" / "x" / "x-stream-state.json"
CONFIG_FILE = WORKSPACE_ROOT / "data" / "x" / "x-stream-config.json"

# X API v2 エンドポイント
STREAM_URL = "https://api.x.com/2/tweets/search/stream"
RULES_URL = "https://api.x.com/2/tweets/search/stream/rules"


def get_bearer_token() -> str:
    """Bearer Tokenを取得"""
    # 環境変数から取得
    token = os.environ.get("X_BEARER_TOKEN")
    if token:
        return token

    # ファイルから取得
    if BEARER_TOKEN_FILE.exists():
        with open(BEARER_TOKEN_FILE) as f:
            data = json.load(f)
            return data.get("bearer_token", "")

    raise ValueError("Bearer Token not found. Set X_BEARER_TOKEN or create data/x/x-bearer-token.json")


def get_webhook_url() -> Optional[str]:
    """Discord Webhook URLを取得"""
    if WEBHOOK_FILE.exists():
        with open(WEBHOOK_FILE) as f:
            data = json.load(f)
            return data.get("webhook_url")
    return None


def get_headers(token: str) -> dict:
    """APIヘッダーを生成"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def get_rules(token: str) -> dict:
    """現在のルールを取得"""
    response = requests.get(RULES_URL, headers=get_headers(token))
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 403:
        print("❌ 403 Forbidden - Bearer Tokenが正しいか、Filtered Stream権限があるか確認してください")
        return {}
    else:
        print(f"❌ Error {response.status_code}: {response.text}")
        return {}


def add_rules(token: str, rules: list) -> bool:
    """ルールを追加"""
    payload = {"add": rules}
    response = requests.post(RULES_URL, headers=get_headers(token), json=payload)
    if response.status_code == 201:
        print("✅ ルールを追加しました")
        return True
    else:
        print(f"❌ Error {response.status_code}: {response.text}")
        return False


def delete_rules(token: str, ids: list) -> bool:
    """ルールを削除"""
    payload = {"delete": {"ids": ids}}
    response = requests.post(RULES_URL, headers=get_headers(token), json=payload)
    if response.status_code == 200:
        print("✅ ルールを削除しました")
        return True
    else:
        print(f"❌ Error {response.status_code}: {response.text}")
        return False


def clear_all_rules(token: str) -> bool:
    """全ルールを削除"""
    rules = get_rules(token)
    if not rules or "data" not in rules:
        print("📭 削除するルールがありません")
        return True

    ids = [rule["id"] for rule in rules["data"]]
    return delete_rules(token, ids)


def send_to_discord(webhook_url: str, tweet: dict) -> bool:
    """Discordに通知"""
    tweet_id = tweet.get("id", "")
    text = tweet.get("text", "")
    author_id = tweet.get("author_id", "")
    created_at = tweet.get("created_at", "")

    # ツイートURL
    tweet_url = f"https://x.com/i/web/status/{tweet_id}"

    # Embed作成
    embed = {
        "title": "🐦 新規ツイート検知",
        "description": text[:500] + ("..." if len(text) > 500 else ""),
        "url": tweet_url,
        "color": 0x1DA1F2,  # Twitter Blue
        "fields": [
            {"name": "Author ID", "value": author_id, "inline": True},
            {"name": "Tweet ID", "value": tweet_id, "inline": True},
        ],
        "timestamp": created_at,
    }

    payload = {
        "username": "X Stream Bot",
        "embeds": [embed],
        "content": "<@&1475432244725288973> 新規ツイートを検知しました",
    }

    response = requests.post(webhook_url, json=payload)
    if response.status_code == 204:
        print(f"✅ Discord通知完了: {tweet_id}")
        return True
    else:
        print(f"❌ Discord通知失敗: {response.status_code}")
        return False


def save_state(tweet_id: str, tweet_time: str):
    """状態を保存"""
    state = {"last_tweet_id": tweet_id, "last_tweet_at": tweet_time}
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def stream_tweets(token: str, webhook_url: Optional[str] = None):
    """ストリームを開始"""
    print("🚀 ストリーム開始...")

    # ツイートフィールドを指定
    params = {
        "tweet.fields": "created_at,author_id,public_metrics,entities,attachments",
        "expansions": "author_id",
        "user.fields": "name,username",
    }

    response = requests.get(
        STREAM_URL,
        headers=get_headers(token),
        params=params,
        stream=True,
    )

    if response.status_code != 200:
        print(f"❌ 接続失敗: {response.status_code} - {response.text}")
        return

    print("📡 接続成功。ツイートを監視中...")

    for line in response.iter_lines():
        if not line:
            continue

        try:
            data = json.loads(line)

            # エラーチェック
            if "errors" in data:
                print(f"⚠️ Error: {data['errors']}")
                continue

            # ツイートデータ
            if "data" in data:
                tweet = data["data"]
                tweet_id = tweet.get("id")
                text = tweet.get("text", "")
                created_at = tweet.get("created_at", "")

                print(f"\n🐦 ツイート検知: {tweet_id}")
                print(f"   {text[:100]}...")

                # 状態保存
                save_state(tweet_id, created_at)

                # Discord通知
                if webhook_url:
                    send_to_discord(webhook_url, tweet)

        except json.JSONDecodeError:
            continue
        except Exception as e:
            print(f"❌ Error: {e}")


def cmd_test(args):
    """設定確認"""
    print("🔍 設定確認中...")

    try:
        token = get_bearer_token()
        print(f"✅ Bearer Token: {token[:20]}...")
    except ValueError as e:
        print(f"❌ {e}")
        return 1

    webhook = get_webhook_url()
    if webhook:
        print(f"✅ Discord Webhook: {webhook[:50]}...")
    else:
        print("⚠️ Discord Webhook未設定")

    # ルール確認
    rules = get_rules(token)
    if rules and "data" in rules:
        print(f"📋 現在のルール: {len(rules['data'])}件")
        for rule in rules["data"]:
            print(f"   - {rule.get('value', '')} (tag: {rule.get('tag', 'N/A')})")
    else:
        print("📭 ルール未設定")

    return 0


def cmd_setup(args):
    """デフォルトルールを設定"""
    print("🔧 デフォルトルール設定中...")

    token = get_bearer_token()

    # 既存ルールをクリア
    clear_all_rules(token)

    # デフォルトルール（hAru_mAki_chの新規投稿）
    default_rules = [
        {
            "value": "from:hAru_mAki_ch -is:retweet -is:reply",
            "tag": "haru_maki_new_posts",
        }
    ]

    if add_rules(token, default_rules):
        print("✅ セットアップ完了")
        return 0
    return 1


def cmd_add(args):
    """カスタムルールを追加"""
    token = get_bearer_token()

    rule = {"value": args.value}
    if args.tag:
        rule["tag"] = args.tag

    if add_rules(token, [rule]):
        return 0
    return 1


def cmd_rules(args):
    """ルール一覧表示"""
    token = get_bearer_token()
    rules = get_rules(token)

    if not rules or "data" not in rules:
        print("📭 ルール未設定")
        return 0

    print(f"📋 現在のルール: {len(rules['data'])}件")
    for i, rule in enumerate(rules["data"], 1):
        print(f"\n{i}. {rule.get('value', '')}")
        print(f"   ID: {rule.get('id', '')}")
        print(f"   Tag: {rule.get('tag', 'N/A')}")

    return 0


def cmd_clear(args):
    """全ルール削除"""
    token = get_bearer_token()
    if clear_all_rules(token):
        return 0
    return 1


def cmd_stream(args):
    """ストリーム開始"""
    token = get_bearer_token()
    webhook_url = get_webhook_url() if not args.no_notify else None

    try:
        stream_tweets(token, webhook_url)
    except KeyboardInterrupt:
        print("\n⏹️ ストリーム停止")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def cmd_test_webhook(args):
    """Webhookテスト"""
    webhook_url = get_webhook_url()
    if not webhook_url:
        print("❌ Webhook URL未設定")
        return 1

    # テスト用ツイート
    test_tweet = {
        "id": "test123456789",
        "text": "これはテストツイートです",
        "author_id": "test_author",
        "created_at": "2026-03-09T12:00:00.000Z",
    }

    if send_to_discord(webhook_url, test_tweet):
        print("✅ Webhookテスト成功")
        return 0
    return 1


def main():
    parser = argparse.ArgumentParser(description="X Filtered Stream Client")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # test
    subparsers.add_parser("test", help="設定確認")

    # setup
    subparsers.add_parser("setup", help="デフォルトルール設定")

    # add
    add_parser = subparsers.add_parser("add", help="ルール追加")
    add_parser.add_argument("value", help="ルール値 (例: from:user -is:retweet)")
    add_parser.add_argument("--tag", help="ルールタグ")

    # rules
    subparsers.add_parser("rules", help="ルール一覧")

    # clear
    subparsers.add_parser("clear", help="全ルール削除")

    # stream
    stream_parser = subparsers.add_parser("stream", help="ストリーム開始")
    stream_parser.add_argument("--no-notify", action="store_true", help="Discord通知なし")

    # test-webhook
    subparsers.add_parser("test-webhook", help="Webhookテスト")

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
