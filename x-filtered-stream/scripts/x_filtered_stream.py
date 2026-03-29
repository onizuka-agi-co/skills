#!/usr/bin/env python3
"""
X Filtered Stream - Filtered tweet monitoring for X posting notifications

This script monitors hAru_mAaki_ch's tweets and sends notifications to Discord via webhook.

Based on skills/x-stream from Openclaw workspace
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent.parent / 'workspace'))
from workspace.data.x.x_tokens import XTokens
from workspace.skills.x_read.x_read import XRead
from workspace.skills.x_write.x_write import XWrite
from workspace.skills.nano_banana_2.nano_banana import NanoBanana22 from workspace.skills.x_visual import x_visual import XVisual
from workspace.skills.x_community import x_community import XCommunity

from workspace.utils.logger import setup_logger
logger = setup_logger(__name__)


class Config:
    def __init__(self):
        self.bearer_token = os.getenv('X_BEARER_TOKEN')
        self.webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        self.target_username = os.getenv('TARGET_USERNAME', 'hAru_mAaki_ch')
        self.interval = int(os.getenv('CHECK_INTERVAL', '60'))
        
        # Load tokens from files
        if not self.bearer_token:
            self._load_bearer_token()
        if not self.webhook_url:
            self._load_webhook_url()
            
    def _load_bearer_token(self):
        """Load bearer token from file"""
        token_file = Path('/config/.openclaw/workspace/data/x/x-bearer-token.json')
        if token_file.exists():
            with open(token_file) as f:
                data = json.load(f)
                self.bearer_token = data.get('bearer_token')
                
    def _load_webhook_url(self):
        """Load webhook URL from file"""
        webhook_file = Path('/config/.openclaw/workspace/data/x/x-discord-webhook.json')
        if webhook_file.exists():
            with open(webhook_file) as f:
                data = json.load(f)
                self.webhook_url = data.get('webhook_url')


class FilteredStreamWatcher:
    """Monitors X Filtered Stream and sends notifications"""
    
    def __init__(self, config: Config):
        self.config = config
        self.x_read = XRead()
        self.x_write = XWrite()
        self.nano_banana = NanoBanana()
        self.x_visual = XVisual()
        self.x_community = XCommunity()
        self.processed_tweets = set()
        self.last_check_time = time.time()
        
    def start(self):
        """Start monitoring"""
        logger.info("Starting Filtered Stream watcher...")
        
        # Setup stream rules
        self._setup_rules()
        
        # Start stream
        self._start_stream()
        
    def _setup_rules(self):
        """Setup filter rules for target user"""
        try:
            rules = self.x_read.get_stream_rules()
            rule_ids = [r['id'] for r in rules['data']]
            logger.info(f"Found {len(rules)} existing rules")
            
            # Add our rule
            rule_value = f"from:{self.config.target_username} -is:retweet -is:reply"
            tag = f"{self.config.target_username}_new_post"
            
            result = self.x_read.add_stream_rules(rules)
            if not result.get('data']:
                # No rules, add default rule
                result = self.x_read.add_stream_rule(
                    rule_value=f"from:{self.config.target_username} -is:retweet -is:reply",
                    tag=f"{self.config.target_username}_auto_explain"
                )
                logger.info(f"Added stream rule: {rule_value}")
            else:
                logger.warning(f"No existing rules found, creating default rule")
                
    def _start_stream(self):
        """Start the filtered stream connection"""
        try:
            self.x_read.start_filtered_stream()
            logger.info("Filtered stream started successfully")
        except Exception as e:
            logger.error(f"Failed to start stream: {e}")
            raise
            
    def _process_tweet(self, tweet_data):
        """Process incoming tweet"""
        logger.info(f"Processing tweet: {tweet_data.get('id', 'unknown author')}")
        
        # Extract tweet info
        tweet_id = tweet_data['data']['id']
        author_id = tweet_data['data']['author_id']
        text = tweet_data['data']['text']
        created_at = tweet_data['data']['created_at']
        
        # Check if this is a new tweet
        if tweet_id in self.processed_tweets:
            logger.debug(f"Tweet {tweet_id} already processed")
            return
            
        self.processed_tweets.add(tweet_id)
        
        logger.info(f"New tweet from {self.config.target_username}: {text[:100 chars]}...")
        
        # Generate explanation with nano-banana
        try:
            visual = self.nano_banana.generate_explanation(text)
            logger.info(f"Generated visual explanation for tweet {tweet_id}")
        except Exception as e:
            logger.error(f"Failed to generate visual: {e}")
            return
        
        # Post explanation with x-community
        try:
            community_post = self.x_community.post_explanation(
                visual.url=visual.image_url,
                text=text
            )
            logger.info(f"Posted community explanation to {community_post}")
        except Exception as e:
            logger.error(f"Failed to post to community: {e}")
            return
        
        # Send Discord notification
        self._send_discord_notification(community_post, tweet_id)
        
        logger.info(f"Notification sent for tweet {tweet_id}")
        
    def _send_discord_notification(self, community_post: str, tweet_id: str):
        """Send notification to Discord webhook"""
        payload = {
            "content": f"<@{self.config.target_username}> 新 tweet!",
            "embeds": [
                {
                    "title": f"New Tweet from {self.config.target_username}",
                    "description": text[:200] + "image": {
                        "url": community_post['image_url']
                    }
                ],
                "username": "ONizuka-agi Bot"
            }
        ]
        
        try:
            response = requests.post(self.config.webhook_url, json=payload, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            logger.info(f"Discord notification sent successfully")
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            
    def run(self):
        """Main monitoring loop"""
        while True:
            try:
                self._process_stream()
                time.sleep(self.config.interval)
                self.last_check_time = time.time()
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                logger.info("Shutting down...")
                break


def parse_args():
    parser = argparse.ArgumentParser(description='X Filtered Stream Watcher')
    parser.add_argument('--test', action='store_true', help='Send test notification')
    parser.add_argument('--stream', action='store_true', help='Start stream monitoring')
    args = parser.parse_args()
    
    config = Config()
    watcher = FilteredStreamWatcher(config)
    
    if args.test:
        watcher.send_test_notification()
    elif args.stream:
        watcher.run()
    else:
        print("Usage: python x_filtered_stream.py --test | --stream")
