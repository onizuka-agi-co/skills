#!/usr/bin/env python3
"""
X Filtered Stream Client
リアルタイムでツイートを監視し、Discordに通知する
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import requests

# 設定パス
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = WORKSPACE_ROOT / "data" / "x"
BEARER_TOKEN_FILE = DATA_DIR / "x-bearer-token.json"
WEBHOOK_FILE = DATA_DIR / "x-discord-webhook.json"
STATE_FILE = DATA_DIR / "x-stream-state.json"
CONFIG_FILE = DATA_DIR / "x-stream-config.json"

# APIエンドポイント
BASE_URL = "https://api.x.com/2"
STREAM_URL = f"{BASE_URL}/tweets/search/stream"
RULES_URL = f"{STREAM_URL}/rules"

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


def load_bearer_token() -> str:
    """Bearer Tokenを読み込む"""
    # 環境変数優先
    token = os.environ.get("X_BEARER_TOKEN")
    if token:
        return token
    
    # ファイルから読み込み
    if BEARER_TOKEN_FILE.exists():
        with open(BEARER_TOKEN_FILE) as f:
            data = json.load(f)
            return data.get("bearer_token", "")
    
    raise ValueError("Bearer Token not found. Set X_BEARER_TOKEN or create data/x/x-bearer-token.json")


def load_webhook_url() -> Optional[str]:
    """Discord Webhook URLを読み込む"""
    # 環境変数優先
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if url:
        return url
    
    # ファイルから読み込み
    if WEBHOOK_FILE.exists():
        with open(WEBHOOK_FILE) as f:
            data = json.load(f)
            return data.get("webhook_url")
    return None


def load_state() -> dict:
    """状態を読み込む"""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    """状態を保存"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


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
        print(f"❌ 403 Forbidden - Filtered Stream権限が必要")
        return {"data": []}
    else:
        print(f"❌ ルール取得エラー: {resp.status_code}")
        print(resp.text)
        return {"data": []}


def add_rules(token: str, rules: list) -> bool:
    """ルールを追加"""
    payload = {"add": rules}
    resp = requests.post(RULES_URL, headers=get_headers(token), json=payload)
    
    if resp.status_code == 201:
        print(f"✅ ルール追加成功: {len(rules)}件")
        return True
    else:
        print(f"❌ ルール追加エラー: {resp.status_code}")
        print(resp.text)
        return False


def delete_all_rules(token: str) -> bool:
    """全ルールを削除"""
    rules = get_rules(token)
    if not rules.get("data"):
        print("📋 削除するルールなし")
        return True
    
    ids = [r["id"] for r in rules["data"]]
    payload = {"delete": {"ids": ids}}
    resp = requests.post(RULES_URL, headers=get_headers(token), json=payload)
    
    if resp.status_code == 200:
        print(f"✅ ルール削除成功: {len(ids)}件")
        return True
    else:
        print(f"❌ ルール削除エラー: {resp.status_code}")
        print(resp.text)
        return False


def send_discord_notification(webhook_url: str, tweet: dict) -> bool:
    """Discordに通知"""
    tweet_id = tweet.get("id", "")
    text = tweet.get("text", "")
    author_id = tweet.get("author_id", "")
    created_at = tweet.get("created_at", "")
    
    # ツイートURL
    tweet_url = f"https://x.com/i/status/{tweet_id}"
    
    # Embed形式で通知
    payload = {
        "content": "🐦 新規投稿を検知しました！",
        "embeds": [{
            "title": "📝 ツイート内容",
            "description": text[:500] + ("..." if len(text) > 500 else ""),
            "url": tweet_url,
            "color": 1942002,  # Xの青色
            "fields": [
                {"name": "投稿者ID", "value": author_id, "inline": True},
                {"name": "投稿時刻", "value": created_at, "inline": True}
            ],
            "footer": {"text": "X Filtered Stream"}
        }],
        "allowed_mentions": {"parse": []}
    }
    
    try:
        resp = requests.post(webhook_url, json=payload)
        if resp.status_code == 204:
            print(f"✅ Discord通知成功: {tweet_id}")
            return True
        else:
            print(f"❌ Discord通知エラー: {resp.status_code}")
            print(resp.text)
            return False
    except Exception as e:
        print(f"❌ Discord通知例外: {e}")
        return False


def stream_tweets(token: str, webhook_url: Optional[str] = None):
    """ストリーミング開始"""
    print("🔄 ストリーミング開始...")
    
    params = {
        "tweet.fields": ",".join(DEFAULT_TWEET_FIELDS)
    }
    
    try:
        with requests.get(
            STREAM_URL,
            headers=get_headers(token),
            params=params,
            stream=True,
            timeout=90
        ) as resp:
            if resp.status_code != 200:
                print(f"❌ ストリーム接続エラー: {resp.status_code}")
                print(resp.text)
                return
            
            print("✅ ストリーム接続成功")
            
            for line in resp.iter_lines():
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    
                    # エラー処理
                    if "errors" in data:
                        print(f"⚠️ エラー: {data['errors']}")
                        continue
                    
                    # ツイート処理
                    if "data" in data:
                        tweet = data["data"]
                        tweet_id = tweet.get("id", "")
                        text = tweet.get("text", "")[:100]
                        
                        print(f"📨 ツイート検知: {tweet_id}")
                        print(f"   {text}...")
                        
                        # 状態保存
                        save_state({
                            "last_tweet_id": tweet_id,
                            "last_tweet_at": tweet.get("created_at", "")
                        })
                        
                        # Discord通知
                        if webhook_url:
                            send_discord_notification(webhook_url, tweet)
                
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"❌ 処理エラー: {e}")
                    continue
    
    except requests.exceptions.Timeout:
        print("⏰ 接続タイムアウト - 再接続中...")
        time.sleep(5)
        stream_tweets(token, webhook_url)
    except requests.exceptions.RequestException as e:
        print(f"❌ 接続エラー: {e}")
        print("5秒後に再接続...")
        time.sleep(5)
        stream_tweets(token, webhook_url)


def test_connection(token: str) -> bool:
    """接続テスト"""
    print("🔍 接続テスト...")
    
    # ルール取得でテスト
    rules = get_rules(token)
    if "data" in rules:
        print(f"✅ 接続成功 - 現在のルール: {len(rules.get('data', []))}件")
        return True
    return False


def test_webhook(webhook_url: str) -> bool:
    """Webhookテスト"""
    print("🔍 Webhookテスト...")
    
    payload = {
        "content": "🧪 X Filtered Stream テスト通知",
        "embeds": [{
            "title": "テスト",
            "description": "これはテスト通知です",
            "color": 65280
        }]
    }
    
    try:
        resp = requests.post(webhook_url, json=payload)
        if resp.status_code == 204:
            print("✅ Webhookテスト成功")
            return True
        else:
            print(f"❌ Webhookテストエラー: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ Webhookテスト例外: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="X Filtered Stream Client")
    parser.add_argument("command", choices=[
        "test", "test-webhook", "setup", "rules", "clear", "add", "stream"
    ], help="実行コマンド")
    parser.add_argument("--rule", help="追加するルール")
    parser.add_argument("--tag", help="ルールのタグ")
    
    args = parser.parse_args()
    
    try:
        token = load_bearer_token()
        webhook_url = load_webhook_url()
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    if args.command == "test":
        test_connection(token)
    
    elif args.command == "test-webhook":
        if not webhook_url:
            print("❌ Webhook URL未設定")
            sys.exit(1)
        test_webhook(webhook_url)
    
    elif args.command == "setup":
        print("📋 デフォルトルール設定中...")
        delete_all_rules(token)
        add_rules(token, DEFAULT_RULES)
        print("\n現在のルール:")
        rules = get_rules(token)
        for r in rules.get("data", []):
            print(f"  - {r.get('tag', 'no-tag')}: {r.get('value', '')}")
    
    elif args.command == "rules":
        print("📋 現在のルール:")
        rules = get_rules(token)
        if not rules.get("data"):
            print("  (ルールなし)")
        else:
            for r in rules["data"]:
                print(f"  - [{r.get('tag', 'no-tag')}] {r.get('value', '')}")
    
    elif args.command == "clear":
        delete_all_rules(token)
    
    elif args.command == "add":
        if not args.rule:
            print("❌ --rule が必要です")
            sys.exit(1)
        rule = {"value": args.rule}
        if args.tag:
            rule["tag"] = args.tag
        add_rules(token, [rule])
    
    elif args.command == "stream":
        print(f"🌐 Webhook: {'設定済み' if webhook_url else '未設定'}")
        print("🔄 ストリーミング開始 (Ctrl+C で終了)")
        stream_tweets(token, webhook_url)


if __name__ == "__main__":
    main()
