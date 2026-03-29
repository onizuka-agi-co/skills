#!/usr/bin/env python3
"""
X API Read Client for OpenClaw
Handles OAuth2 token management and READ-only API calls
Supports media download from tweets
"""

import json
import os
import urllib.request
import urllib.parse
import urllib.error
import base64
import ssl
from datetime import datetime, timezone
from pathlib import Path
from x_cache import XCache

# Token file paths (relative to workspace root)
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "x"
TOKEN_FILE = DATA_DIR / "x-tokens.json"
CLIENT_CREDENTIALS_FILE = DATA_DIR / "x-client-credentials.json"
MEDIA_DIR = DATA_DIR / "media"

class XReadClient:
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None
        self.client_id = None
        self.client_secret = None
        self._load_tokens()
        self._load_credentials()
        self.cache = XCache()
    
    def _load_tokens(self):
        if TOKEN_FILE.exists():
            with open(TOKEN_FILE, 'r') as f:
                data = json.load(f)
                self.access_token = data.get('access_token')
                self.refresh_token = data.get('refresh_token')
                if 'expires_in' in data:
                    self.expires_at = datetime.now(timezone.utc).timestamp() + data['expires_in']
    
    def _load_credentials(self):
        if CLIENT_CREDENTIALS_FILE.exists():
            with open(CLIENT_CREDENTIALS_FILE, 'r') as f:
                data = json.load(f)
                self.client_id = data.get('client_id')
                self.client_secret = data.get('client_secret')
    
    def _save_tokens(self, data):
        with open(TOKEN_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        self._load_tokens()
    
    def is_token_expired(self):
        if not self.expires_at:
            return True
        return datetime.now(timezone.utc).timestamp() > (self.expires_at - 300)
    
    def refresh_access_token(self):
        if not self.refresh_token or not self.client_id or not self.client_secret:
            raise Exception("Missing refresh token or client credentials")
        
        basic_auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        body = urllib.parse.urlencode({
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token
        })
        
        req = urllib.request.Request(
            "https://api.x.com/2/oauth2/token",
            data=body.encode(),
            headers={
                'Authorization': f'Basic {basic_auth}',
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            method='POST'
        )
        
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            self._save_tokens(data)
            return data
    
    def _ensure_valid_token(self):
        if self.is_token_expired():
            self.refresh_access_token()
        return self.access_token
    
    def _api_request(self, endpoint, params=None, use_cache=True):
        # Check cache first
        if use_cache:
            cached = self.cache.get(endpoint, params)
            if cached:
                return cached
        
        token = self._ensure_valid_token()
        url = f"https://api.x.com{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
        
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
        
        # Cache the response
        if use_cache:
            self.cache.set(endpoint, data, params)
        
        return data
    
    # === READ operations ===
    
    def get_me(self):
        """Get current authenticated user"""
        return self._api_request('/2/users/me')
    
    def get_user(self, username):
        """Get user by username"""
        return self._api_request(f'/2/users/by/username/{username}')
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        return self._api_request(f'/2/users/{user_id}')
    
    def get_tweet(self, tweet_id, tweet_fields=None, expansions=None, media_fields=None):
        """Get a tweet by ID"""
        params = {}
        if tweet_fields:
            params['tweet.fields'] = ','.join(tweet_fields)
        if expansions:
            params['expansions'] = ','.join(expansions)
        if media_fields:
            params['media.fields'] = ','.join(media_fields)
        return self._api_request(f'/2/tweets/{tweet_id}', params=params if params else None)
    
    def get_tweet_with_media(self, tweet_id):
        """Get a tweet by ID with media expansions"""
        params = {
            'tweet.fields': 'created_at,public_metrics,author_id,attachments,entities,community_id',
            'expansions': 'attachments.media_keys,author_id',
            'media.fields': 'url,preview_image_url,type,duration_ms,variants,alt_text',
            'user.fields': 'name,username,profile_image_url'
        }
        return self._api_request(f'/2/tweets/{tweet_id}', params=params)
    
    def download_media(self, media_url, save_path):
        """Download a single media file to local path (public URL, no auth needed)"""
        req = urllib.request.Request(media_url, headers={'User-Agent': 'OpenClaw/1.0'})
        ssl_context = ssl.create_default_context()
        
        # Ensure parent directory exists (not the file path itself)
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with urllib.request.urlopen(req, context=ssl_context) as resp:
            content = resp.read()
            with open(save_path, 'wb') as f:
                f.write(content)
        return save_path
    
    def download_all_media(self, media_items, tweet_id, output_dir=None):
        """Download all media files from tweet"""
        if output_dir is None:
            output_dir = MEDIA_DIR / str(tweet_id)
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        downloaded = []
        
        for i, media in enumerate(media_items):
            media_type = media.get('type', 'unknown')
            media_url = media.get('url') or media.get('preview_image_url')
            
            if not media_url:
                # For videos, find the best variant
                variants = media.get('variants', [])
                if variants:
                    # Prefer higher bitrate
                    video_variants = [v for v in variants if v.get('content_type', '').startswith('video/')]
                    if video_variants:
                        video_variants.sort(key=lambda x: x.get('bit_rate', 0), reverse=True)
                        media_url = video_variants[0].get('url')
            
            if not media_url:
                continue
            
            # Determine extension
            if media_type == 'photo':
                ext = '.jpg'
            elif media_type == 'video' or media_type == 'animated_gif':
                ext = '.mp4'
            else:
                ext = '.bin'
            
            filename = f"media_{i+1}{ext}"
            filepath = output_dir / filename
            
            try:
                self.download_media(media_url, filepath)
                downloaded.append({
                    'path': str(filepath),
                    'type': media_type,
                    'url': media_url
                })
            except Exception as e:
                downloaded.append({
                    'error': str(e),
                    'url': media_url,
                    'type': media_type
                })
        
        return downloaded
    
    def get_timeline(self, user_id, max_results=10, exclude=None):
        """Get user's timeline"""
        params = {'max_results': max_results}
        if exclude:
            params['exclude'] = ','.join(exclude)
        return self._api_request(f'/2/users/{user_id}/timelines/reverse_chronological', params=params)
    
    def get_mentions(self, user_id, max_results=10):
        """Get user's mentions"""
        return self._api_request(f'/2/users/{user_id}/mentions', params={'max_results': max_results})
    
    def get_tweets(self, user_id, max_results=10, exclude=None):
        """Get user's tweets"""
        params = {'max_results': max_results}
        if exclude:
            params['exclude'] = ','.join(exclude)
        return self._api_request(f'/2/users/{user_id}/tweets', params=params)
    
    def search_recent(self, query, max_results=10):
        """Search recent tweets"""
        return self._api_request('/2/tweets/search/recent', params={'query': query, 'max_results': max_results})

    def get_bookmarks(self, max_results=10):
        """Get user's bookmarks (requires bookmark.read scope)"""
        me = self.get_me()
        user_id = me['data']['id']
        params = {
            'max_results': max_results,
            'tweet.fields': 'created_at,public_metrics,author_id,text,entities',
            'expansions': 'author_id',
            'user.fields': 'name,username,profile_image_url'
        }
        return self._api_request(f'/2/users/{user_id}/bookmarks', params=params)
    
    def get_bookmark_folders(self):
        """Get user's bookmark folders (requires bookmark.read scope)"""
        me = self.get_me()
        user_id = me['data']['id']
        return self._api_request(f'/2/users/{user_id}/bookmarks/folders')
    
    def get_bookmarks_by_folder(self, folder_id, max_results=10):
        """Get bookmarks in a specific folder (requires bookmark.read scope)"""
        me = self.get_me()
        user_id = me['data']['id']
        params = {
            'max_results': max_results,
            'tweet.fields': 'created_at,public_metrics,author_id,text,entities',
            'expansions': 'author_id',
            'user.fields': 'name,username,profile_image_url'
        }
        return self._api_request(f'/2/users/{user_id}/bookmarks/folders/{folder_id}', params=params)


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("X API Read Client")
        print("\nUsage: python x_read.py <command> [args...]")
        print("\nCommands:")
        print("  me                    - Get current user info")
        print("  user <username>       - Get user by username")
        print("  userid <user_id>      - Get user by ID")
        print("  tweet <tweet_id>      - Get tweet by ID")
        print("  tweet-media <tweet_id> [output_dir] - Get tweet with media, download to output_dir")
        print("  timeline [max]        - Get timeline (default: 10)")
        print("  mentions [max]        - Get mentions (default: 10)")
        print("  tweets [max]          - Get your tweets (default: 10)")
        print("  search <query> [max]  - Search tweets (default: 10)")
        print("  bookmarks [max]       - Get your bookmarks (default: 10)")
        print("  bookmark-folders      - Get your bookmark folders")
        print("  bookmark-folder <folder_id> [max] - Get bookmarks in folder")
        print("  refresh               - Refresh access token")
        sys.exit(1)
    
    client = XReadClient()
    command = sys.argv[1]
    
    try:
        if command == "me":
            result = client.get_me()
            print(json.dumps(result, indent=2))
        
        elif command == "user":
            username = sys.argv[2]
            result = client.get_user(username)
            print(json.dumps(result, indent=2))
        
        elif command == "userid":
            user_id = sys.argv[2]
            result = client.get_user_by_id(user_id)
            print(json.dumps(result, indent=2))
        
        elif command == "tweet":
            tweet_id = sys.argv[2]
            save_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else MEDIA_DIR / tweet_id
            
            # Get tweet with media
            result = client.get_tweet_with_media(tweet_id)
            
            # Download media if exists
            if 'includes' in result and 'media' in result['includes']:
                downloaded = client.download_all_media(result['includes']['media'], tweet_id, save_dir)
                result['media_files'] = [d['path'] for d in downloaded if 'path' in d]
            
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # Display saved media info
            if result.get('media_files'):
                print(f"\n📁 Media saved to: {save_dir}")
                for f in result['media_files']:
                    print(f"  📎 {f}")
        
        elif command == "tweet-media":
            # Get tweet with media and download
            tweet_id = sys.argv[2]
            save_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else MEDIA_DIR / tweet_id
            
            result = client.get_tweet_with_media(tweet_id)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # Download media if exists
            if 'includes' in result and 'media' in result['includes']:
                print(f"\n📁 Downloading media to: {save_dir}")
                downloaded = client.download_all_media(result['includes']['media'], tweet_id, save_dir)
                
                success_count = 0
                for item in downloaded:
                    if 'path' in item:
                        print(f"  ✅ Saved: {item['path']} ({item['type']})")
                        success_count += 1
                    else:
                        print(f"  ❌ Failed: {item['url']} - {item.get('error', 'Unknown error')}")
                
                if success_count > 0:
                    print(f"\n✅ Downloaded {success_count} file(s)")
                    result['downloaded_files'] = [d['path'] for d in downloaded if 'path' in d]
            else:
                print("\n⚠️ No media found in this tweet")
        
        elif command == "timeline":
            max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            me = client.get_me()
            user_id = me['data']['id']
            result = client.get_timeline(user_id, max_results)
            print(json.dumps(result, indent=2))
        
        elif command == "mentions":
            max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            me = client.get_me()
            user_id = me['data']['id']
            result = client.get_mentions(user_id, max_results)
            print(json.dumps(result, indent=2))
        
        elif command == "tweets":
            max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            me = client.get_me()
            user_id = me['data']['id']
            result = client.get_tweets(user_id, max_results)
            print(json.dumps(result, indent=2))
        
        elif command == "search":
            query = sys.argv[2]
            max_results = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            result = client.search_recent(query, max_results)
            print(json.dumps(result, indent=2))
        
        elif command == "bookmarks":
            max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            result = client.get_bookmarks(max_results)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif command == "bookmark-folders":
            result = client.get_bookmark_folders()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif command == "bookmark-folder":
            folder_id = sys.argv[2]
            max_results = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            result = client.get_bookmarks_by_folder(folder_id, max_results)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        elif command == "refresh":
            result = client.refresh_access_token()
            print(json.dumps(result, indent=2))
        
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
