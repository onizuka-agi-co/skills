#!/usr/bin/env python3
"""
X Community Post Client for OpenClaw
Specialized for posting to X Communities
"""

import json
import urllib.request
import urllib.parse
import urllib.error
import base64
import re
import ssl
from datetime import datetime, timezone
from pathlib import Path

# Token file paths (relative to workspace root)
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "x"
TOKEN_FILE = DATA_DIR / "x-tokens.json"
CLIENT_CREDENTIALS_FILE = DATA_DIR / "x-client-credentials.json"
CONFIG_FILE = DATA_DIR / "x-community-config.json"

# Default community ID
DEFAULT_COMMUNITY_ID = "2010195061309587967"


def extract_tweet_id(url_or_id):
    """Extract tweet ID from URL or return as-is if already an ID"""
    # If it's already a numeric ID
    if url_or_id.isdigit():
        return url_or_id
    # Extract from URL patterns like:
    # https://x.com/username/status/123456789
    # https://twitter.com/username/status/123456789
    match = re.search(r'(?:x\.com|twitter\.com)/\w+/status/(\d+)', url_or_id)
    if match:
        return match.group(1)
    return None


class XCommunityClient:
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None
        self.client_id = None
        self.client_secret = None
        self.community_id = DEFAULT_COMMUNITY_ID
        self._load_tokens()
        self._load_credentials()
        self._load_config()
    
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
    
    def _load_config(self):
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                self.community_id = data.get('community_id', DEFAULT_COMMUNITY_ID)
    
    def _save_tokens(self, data):
        with open(TOKEN_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        self._load_tokens()
    
    def _save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'community_id': self.community_id}, f, indent=2)
    
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
    
    def _api_request(self, method, endpoint, data=None):
        token = self._ensure_valid_token()
        url = f"https://api.x.com{endpoint}"
        
        headers = {'Authorization': f'Bearer {token}'}
        body = None
        
        if data:
            headers['Content-Type'] = 'application/json'
            body = json.dumps(data).encode()
        
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise Exception(f"API error: {e.code} - {error_body}")
    
    def post_to_community(self, text, community_id=None, share_with_followers=True, quote_tweet_id=None, media_ids=None):
        """Post to a community"""
        cid = community_id or self.community_id
        data = {
            'text': text,
            'community_id': cid,
            'share_with_followers': share_with_followers
        }
        if quote_tweet_id:
            data['quote_tweet_id'] = quote_tweet_id
        if media_ids:
            data['media'] = {'media_ids': media_ids}
        return self._api_request('POST', '/2/tweets', data=data)
    
    def upload_media(self, image_path):
        """Upload media to X and return media_id"""
        token = self._ensure_valid_token()
        
        # Read image file
        image_path = Path(image_path)
        if not image_path.exists():
            raise Exception(f"Image file not found: {image_path}")
        
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # Determine media type
        suffix = image_path.suffix.lower()
        media_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
        }
        media_type = media_type_map.get(suffix, 'image/jpeg')
        
        # Upload to media/upload endpoint (v1.1)
        url = "https://upload.twitter.com/1.1/media/upload.json"
        boundary = "----OpenClawBoundary" + str(hash(str(image_path)))[-8:]
        
        body = []
        body.append(f'--{boundary}'.encode())
        body.append(f'Content-Disposition: form-data; name="media"; filename="{image_path.name}"'.encode())
        body.append(f'Content-Type: {media_type}'.encode())
        body.append(b'')
        body.append(image_data)
        body.append(f'--{boundary}--'.encode())
        
        body_bytes = b'\r\n'.join(body)
        
        req = urllib.request.Request(
            url,
            data=body_bytes,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': f'multipart/form-data; boundary={boundary}'
            },
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode())
                return result.get('media_id_string') or result.get('media_id')
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise Exception(f"Media upload error: {e.code} - {error_body}")
    
    def set_community(self, community_id):
        """Set default community ID"""
        self.community_id = community_id
        self._save_config()
        return {'community_id': community_id}
    
    def get_config(self):
        """Get current configuration"""
        return {
            'community_id': self.community_id,
            'community_url': f'https://x.com/i/communities/{self.community_id}'
        }


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("X Community Post Client")
        print("\nUsage: python x_community.py <command> [args...]")
        print("\nCommands:")
        print("  post <text> [--no-share] [--quote <url|id>] [--image <path>]  - Post to community")
        print("  quote <url|id> <text> [--no-share]                            - Quote tweet to community")
        print("  visual-quote <url> [--comment <text>] [--no-share]            - Visual quote with generated image")
        print("  set-community <id>                                            - Set default community ID")
        print("  config                                                        - Show current configuration")
        print("  refresh                                                       - Refresh access token")
        print("\nExamples:")
        print("  post 'Hello community!'")
        print("  post 'Check this out!' --quote https://x.com/user/status/123")
        print("  post 'With image!' --image /path/to/image.png")
        print("  visual-quote https://x.com/user/status/123 --comment 'My explanation'")
        sys.exit(1)
    
    client = XCommunityClient()
    command = sys.argv[1]
    
    try:
        if command == "post":
            if len(sys.argv) < 3:
                print("Usage: python x_community.py post <text> [--no-share] [--quote <url|id>] [--image <path>]")
                sys.exit(1)
            args = sys.argv[2:]
            no_share = '--no-share' in args
            quote_tweet_id = None
            image_path = None
            media_ids = None
            
            # Extract --quote argument
            if '--quote' in args:
                quote_idx = args.index('--quote')
                if quote_idx + 1 < len(args):
                    quote_url = args[quote_idx + 1]
                    quote_tweet_id = extract_tweet_id(quote_url)
                    if not quote_tweet_id:
                        print(f"Error: Invalid quote URL or ID: {quote_url}")
                        sys.exit(1)
            
            # Extract --image argument
            if '--image' in args:
                image_idx = args.index('--image')
                if image_idx + 1 < len(args):
                    image_path = args[image_idx + 1]
                    # Upload image
                    media_id = client.upload_media(image_path)
                    media_ids = [media_id]
            
            # Remove flags from text
            filtered_args = []
            skip_next = False
            for i, a in enumerate(args):
                if skip_next:
                    skip_next = False
                    continue
                if a in ['--quote', '--image']:
                    skip_next = True
                    continue
                if a == '--no-share':
                    continue
                filtered_args.append(a)
            text = ' '.join(filtered_args)
            
            if not text:
                print("Error: No text provided")
                sys.exit(1)
            result = client.post_to_community(text, share_with_followers=not no_share, quote_tweet_id=quote_tweet_id, media_ids=media_ids)
            print(json.dumps(result, indent=2))
        
        elif command == "quote":
            if len(sys.argv) < 4:
                print("Usage: python x_community.py quote <url|id> <text> [--no-share]")
                sys.exit(1)
            quote_url = sys.argv[2]
            quote_tweet_id = extract_tweet_id(quote_url)
            if not quote_tweet_id:
                print(f"Error: Invalid quote URL or ID: {quote_url}")
                sys.exit(1)
            args = sys.argv[3:]
            no_share = '--no-share' in args
            text_args = [a for a in args if a != '--no-share']
            text = ' '.join(text_args)
            if not text:
                print("Error: No text provided")
                sys.exit(1)
            result = client.post_to_community(text, share_with_followers=not no_share, quote_tweet_id=quote_tweet_id)
            print(json.dumps(result, indent=2))
        
        elif command == "set-community":
            if len(sys.argv) < 3:
                print("Usage: python x_community.py set-community <community_id>")
                sys.exit(1)
            community_id = sys.argv[2]
            result = client.set_community(community_id)
            print(json.dumps(result, indent=2))
        
        elif command == "config":
            result = client.get_config()
            print(json.dumps(result, indent=2))
        
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
