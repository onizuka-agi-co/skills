#!/usr/bin/env python3
"""
X API Write Client for OpenClaw
Handles OAuth2 token management and WRITE-only API calls
Supports media upload for image attachments
"""

import json
import urllib.request
import urllib.parse
import urllib.error
import base64
import mimetypes
from datetime import datetime, timezone
from pathlib import Path

# Token file paths (relative to workspace root)
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "x"
TOKEN_FILE = DATA_DIR / "x-tokens.json"
CLIENT_CREDENTIALS_FILE = DATA_DIR / "x-client-credentials.json"


class XWriteClient:
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.expires_at = None
        self.client_id = None
        self.client_secret = None
        self._load_tokens()
        self._load_credentials()
    
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
    
    def _multipart_upload(self, url, fields, files):
        """Upload files using multipart/form-data"""
        import uuid
        boundary = uuid.uuid4().hex
        
        token = self._ensure_valid_token()
        
        body_parts = []
        
        # Add form fields
        for key, value in fields.items():
            body_parts.append(f'--{boundary}'.encode())
            body_parts.append(f'Content-Disposition: form-data; name="{key}"'.encode())
            body_parts.append(b'')
            body_parts.append(str(value).encode())
        
        # Add files
        for key, (filename, content, content_type) in files.items():
            body_parts.append(f'--{boundary}'.encode())
            body_parts.append(
                f'Content-Disposition: form-data; name="{key}"; filename="{filename}"'.encode()
            )
            body_parts.append(f'Content-Type: {content_type}'.encode())
            body_parts.append(b'')
            body_parts.append(content)
        
        body_parts.append(f'--{boundary}--'.encode())
        body_parts.append(b'')
        
        body = b'\r\n'.join(body_parts)
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': f'multipart/form-data; boundary={boundary}',
        }
        
        req = urllib.request.Request(url, data=body, headers=headers, method='POST')
        
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise Exception(f"Upload error: {e.code} - {error_body}")
    
    # === Media Upload ===
    
    def upload_media(self, image_path_or_url):
        """Upload an image and return media_id"""
        path = Path(image_path_or_url)
        
        # Check if it's a URL
        if str(image_path_or_url).startswith('http://') or str(image_path_or_url).startswith('https://'):
            # Download the image first
            print(f"Downloading image from URL...")
            req = urllib.request.Request(str(image_path_or_url))
            with urllib.request.urlopen(req) as resp:
                content = resp.read()
            filename = str(image_path_or_url).split('/')[-1].split('?')[0]
            content_type = resp.headers.get('Content-Type', 'image/png')
        else:
            # Local file
            if not path.exists():
                raise FileNotFoundError(f"Image file not found: {image_path_or_url}")
            
            with open(path, 'rb') as f:
                content = f.read()
            
            filename = path.name
            content_type = mimetypes.guess_type(str(path))[0] or 'image/png'
        
        # Upload to X API v2
        print(f"Uploading image ({len(content)} bytes)...")
        result = self._multipart_upload(
            "https://api.x.com/2/media/upload",
            fields={'media_category': 'tweet_image'},
            files={'media': (filename, content, content_type)}
        )
        
        if 'data' in result and 'id' in result['data']:
            media_id = result['data']['id']
            print(f"Media uploaded successfully: {media_id}")
            return media_id
        else:
            raise Exception(f"Upload failed: {result}")
    
    # === WRITE operations ===
    
    def post_tweet(self, text, community_id=None, share_with_followers=False, quote_tweet_id=None, media_ids=None, reply_to_tweet_id=None):
        """Post a tweet (optionally to a community, as a quote retweet, or as a reply)"""
        data = {'text': text}
        if community_id:
            data['community_id'] = community_id
            if share_with_followers:
                data['share_with_followers'] = True
        if quote_tweet_id:
            data['quote_tweet_id'] = quote_tweet_id
        if media_ids:
            data['media'] = {'media_ids': media_ids if isinstance(media_ids, list) else [media_ids]}
        if reply_to_tweet_id:
            data['reply'] = {'in_reply_to_tweet_id': reply_to_tweet_id}
        return self._api_request('POST', '/2/tweets', data=data)
    
    def delete_tweet(self, tweet_id):
        """Delete a tweet"""
        return self._api_request('DELETE', f'/2/tweets/{tweet_id}')
    
    def like_tweet(self, tweet_id, user_id):
        """Like a tweet"""
        return self._api_request('POST', f'/2/users/{user_id}/likes', data={'tweet_id': tweet_id})
    
    def unlike_tweet(self, tweet_id, user_id):
        """Unlike a tweet"""
        return self._api_request('DELETE', f'/2/users/{user_id}/likes/{tweet_id}')
    
    def retweet(self, tweet_id, user_id):
        """Retweet a tweet"""
        return self._api_request('POST', f'/2/users/{user_id}/retweets', data={'tweet_id': tweet_id})
    
    def unretweet(self, tweet_id, user_id):
        """Undo a retweet"""
        return self._api_request('DELETE', f'/2/users/{user_id}/retweets/{tweet_id}')
    
    def follow_user(self, target_user_id, source_user_id):
        """Follow a user"""
        return self._api_request('POST', f'/2/users/{source_user_id}/following', data={'target_user_id': target_user_id})
    
    def unfollow_user(self, target_user_id, source_user_id):
        """Unfollow a user"""
        return self._api_request('DELETE', f'/2/users/{source_user_id}/following/{target_user_id}')


def generate_diagram_prompt(text: str, style: str = "abstract") -> str:
    """Generate a diagram prompt from tweet text."""
    # Extract key concepts from text
    keywords = []
    
    # Common tech/AI keywords to highlight
    tech_keywords = [
        "AGI", "AI", "LLM", "GPT", "machine learning", "neural", "transformer",
        "model", "training", "inference", "API", "code", "system", "architecture",
        "data", "algorithm", "optimization", "research", "paper", "framework",
        "agent", "autonomous", "reasoning", "knowledge", "learning"
    ]
    
    text_lower = text.lower()
    for kw in tech_keywords:
        if kw.lower() in text_lower:
            keywords.append(kw)
    
    # Build prompt based on style
    style_prompts = {
        "abstract": "Abstract geometric visualization representing",
        "minimalist": "Minimalist clean diagram showing",
        "tech": "Technical schematic illustration of",
        "artistic": "Artistic conceptual visualization of"
    }
    
    base = style_prompts.get(style, style_prompts["abstract"])
    
    if keywords:
        concept = ", ".join(keywords[:3])
        prompt = f"{base} {concept}. Modern, professional, clean lines, soft colors, high quality"
    else:
        # Generic prompt based on text sentiment
        prompt = f"{base} innovative technology concepts. Modern, professional, elegant design"
    
    # Add style-specific modifiers
    if style == "abstract":
        prompt += ", abstract shapes, flowing forms, gradient colors"
    elif style == "minimalist":
        prompt += ", simple icons, white space, monochrome accents"
    elif style == "tech":
        prompt += ", circuit patterns, data flow, blue tones, precise lines"
    elif style == "artistic":
        prompt += ", vibrant colors, creative composition, dynamic flow"
    
    return prompt


def generate_diagram_image(prompt: str) -> Path:
    """Generate a diagram image using nano-banana-2 skill."""
    import subprocess
    import tempfile
    
    # Path to nano-banana-2 generate script
    workspace_root = Path(__file__).parent.parent.parent.parent
    nano_banana_script = workspace_root / "skills" / "nano-banana-2" / "scripts" / "generate.py"
    output_dir = workspace_root / "temp" / "diagrams"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    import time
    timestamp = int(time.time())
    output_file = output_dir / f"diagram_{timestamp}.png"
    
    # Call nano-banana-2 generate script
    cmd = [
        "uv", "run", str(nano_banana_script),
        "--prompt", prompt,
        "--aspect-ratio", "16:9",
        "--resolution", "1K",
        "--output-format", "png",
        "--output-dir", str(output_dir),
        "--save"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(workspace_root))
    
    if result.returncode != 0:
        print(f"STDERR: {result.stderr}")
        raise Exception(f"Image generation failed: {result.stderr}")
    
    # Find the generated file
    generated_files = list(output_dir.glob("generated_*.png"))
    if generated_files:
        # Return the most recent one
        return max(generated_files, key=lambda p: p.stat().st_mtime)
    
    # Fallback to expected filename
    expected = output_dir / f"generated_1.png"
    if expected.exists():
        return expected
    
    raise Exception("Generated image not found")


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("X API Write Client")
        print("\nUsage: python x_write.py <command> [args...]")
        print("\nCommands:")
        print("  post <text>                      - Post a tweet")
        print("  post-image <image_path> <text>   - Post a tweet with image")
        print("  post-with-diagram <text> [--style <style>] - Post with auto-generated diagram")
        print("  upload <image_path>              - Upload image, returns media_id")
        print("  quote <tweet_id> <text>          - Quote retweet a tweet")
        print("  reply <tweet_id> <text>          - Reply to a tweet")
        print("  community <community_id> <text> [--share] - Post to a community")
        print("  delete <tweet_id>                - Delete a tweet")
        print("  like <tweet_id> [user]           - Like a tweet (user=me or user_id)")
        print("  unlike <tweet_id> [user]         - Unlike a tweet")
        print("  retweet <tweet_id> [user]        - Retweet")
        print("  unretweet <tweet_id> [user]      - Undo retweet")
        print("  follow <user_id> [user]          - Follow a user")
        print("  unfollow <user_id> [user]        - Unfollow a user")
        print("  refresh                          - Refresh access token")
        print("  auth                             - Start OAuth2 authentication flow")
        print("\nDiagram Styles: abstract, minimalist, tech, artistic")
        sys.exit(1)
    
    client = XWriteClient()
    command = sys.argv[1]
    
    def get_my_user_id():
        # Need to use read API to get user_id
        import urllib.request as req
        token = client._ensure_valid_token()
        r = req.Request("https://api.x.com/2/users/me", headers={'Authorization': f'Bearer {token}'})
        with req.urlopen(r) as resp:
            data = json.loads(resp.read().decode())
            return data['data']['id']
    
    try:
        if command == "post":
            text = ' '.join(sys.argv[2:])
            result = client.post_tweet(text)
            print(json.dumps(result, indent=2))
        
        elif command == "upload":
            if len(sys.argv) < 3:
                print("Usage: python x_write.py upload <image_path_or_url>")
                sys.exit(1)
            image_path = sys.argv[2]
            media_id = client.upload_media(image_path)
            print(json.dumps({"media_id": media_id}, indent=2))
        
        elif command == "post-image":
            if len(sys.argv) < 4:
                print("Usage: python x_write.py post-image <image_path_or_url> <text>")
                sys.exit(1)
            image_path = sys.argv[2]
            text = ' '.join(sys.argv[3:])
            
            # Upload image
            media_id = client.upload_media(image_path)
            
            # Post tweet with media
            result = client.post_tweet(text, media_ids=[media_id])
            print(json.dumps(result, indent=2))
        
        elif command == "community":
            if len(sys.argv) < 4:
                print("Usage: python x_write.py community <community_id> <text> [--no-share]")
                print("  Default: share with followers")
                print("  --no-share: community only (not shown to followers)")
                sys.exit(1)
            community_id = sys.argv[2]
            # Find text and --no-share flag (default is share_with_followers=True)
            args = sys.argv[3:]
            no_share = '--no-share' in args
            text_args = [a for a in args if a != '--no-share']
            text = ' '.join(text_args)
            result = client.post_tweet(text, community_id=community_id, share_with_followers=not no_share)
            print(json.dumps(result, indent=2))
        
        elif command == "delete":
            tweet_id = sys.argv[2]
            result = client.delete_tweet(tweet_id)
            print(json.dumps(result, indent=2))
        
        elif command == "quote":
            if len(sys.argv) < 4:
                print("Usage: python x_write.py quote <tweet_id> <text>")
                sys.exit(1)
            quote_tweet_id = sys.argv[2]
            text = ' '.join(sys.argv[3:])
            result = client.post_tweet(text, quote_tweet_id=quote_tweet_id)
            print(json.dumps(result, indent=2))
        
        elif command == "reply":
            if len(sys.argv) < 4:
                print("Usage: python x_write.py reply <tweet_id> <text>")
                sys.exit(1)
            reply_to_tweet_id = sys.argv[2]
            text = ' '.join(sys.argv[3:])
            result = client.post_tweet(text, reply_to_tweet_id=reply_to_tweet_id)
            print(json.dumps(result, indent=2))
        
        elif command == "like":
            tweet_id = sys.argv[2]
            user_id = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "me" else get_my_user_id()
            result = client.like_tweet(tweet_id, user_id)
            print(json.dumps(result, indent=2))
        
        elif command == "unlike":
            tweet_id = sys.argv[2]
            user_id = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "me" else get_my_user_id()
            result = client.unlike_tweet(tweet_id, user_id)
            print(json.dumps(result, indent=2))
        
        elif command == "retweet":
            tweet_id = sys.argv[2]
            user_id = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "me" else get_my_user_id()
            result = client.retweet(tweet_id, user_id)
            print(json.dumps(result, indent=2))
        
        elif command == "unretweet":
            tweet_id = sys.argv[2]
            user_id = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "me" else get_my_user_id()
            result = client.unretweet(tweet_id, user_id)
            print(json.dumps(result, indent=2))
        
        elif command == "follow":
            target_user_id = sys.argv[2]
            source_user_id = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "me" else get_my_user_id()
            result = client.follow_user(target_user_id, source_user_id)
            print(json.dumps(result, indent=2))
        
        elif command == "unfollow":
            target_user_id = sys.argv[2]
            source_user_id = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "me" else get_my_user_id()
            result = client.unfollow_user(target_user_id, source_user_id)
            print(json.dumps(result, indent=2))
        
        elif command == "refresh":
            result = client.refresh_access_token()
            print(json.dumps(result, indent=2))
        
        elif command == "auth":
            # Import and run authentication
            import subprocess
            import sys as sys_module
            auth_script = Path(__file__).parent / "x_auth.py"
            result = subprocess.run([sys_module.executable, str(auth_script)], capture_output=False)
            sys.exit(result.returncode)
        
        elif command == "post-with-diagram":
            if len(sys.argv) < 3:
                print("Usage: python x_write.py post-with-diagram <text> [--style <style>]")
                print("\nGenerate a diagram image from text and post with it.")
                print("\nStyles: abstract, minimalist, tech, artistic")
                sys.exit(1)
            
            # Parse arguments
            args = sys.argv[2:]
            style = "abstract"
            text_args = []
            i = 0
            while i < len(args):
                if args[i] == "--style" and i + 1 < len(args):
                    style = args[i + 1]
                    i += 2
                else:
                    text_args.append(args[i])
                    i += 1
            text = ' '.join(text_args)
            
            # Generate diagram prompt from text
            diagram_prompt = generate_diagram_prompt(text, style)
            print(f"Generated prompt: {diagram_prompt}")
            
            # Generate image using nano-banana-2
            image_path = generate_diagram_image(diagram_prompt)
            print(f"Generated image: {image_path}")
            
            # Upload and post
            media_id = client.upload_media(image_path)
            result = client.post_tweet(text, media_ids=[media_id])
            print(json.dumps(result, indent=2))
        
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
