#!/usr/bin/env python3
"""
X API Client for hAru_mAki_ch
"""

import json
import urllib.request
import urllib.parse
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "x"
TOKEN_FILE = DATA_DIR / "x-tokens-haru.json"
CLIENT_CREDENTIALS_FILE = DATA_DIR / "x-client-credentials-haru.json"


class XHaruClient:
    def __init__(self):
        self.access_token = None
        self.client_id = None
        self.client_secret = None
        self._load_tokens()
        self._load_credentials()
    
    def _load_tokens(self):
        if TOKEN_FILE.exists():
            with open(TOKEN_FILE) as f:
                data = json.load(f)
                self.access_token = data.get('access_token')
    
    def _load_credentials(self):
        if CLIENT_CREDENTIALS_FILE.exists():
            with open(CLIENT_CREDENTIALS_FILE) as f:
                data = json.load(f)
                self.client_id = data.get('client_id')
                self.client_secret = data.get('client_secret')
    
    def _api_request(self, endpoint, params=None):
        url = f"https://api.x.com{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        
        req = urllib.request.Request(
            url,
            headers={'Authorization': f'Bearer {self.access_token}'}
        )
        
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    
    def get_me(self):
        return self._api_request('/2/users/me')
    
    def get_bookmarks(self, max_results=10):
        me = self.get_me()
        user_id = me['data']['id']
        params = {
            'max_results': max_results,
            'tweet.fields': 'created_at,public_metrics,author_id,text,entities',
            'expansions': 'author_id',
            'user.fields': 'name,username,profile_image_url'
        }
        return self._api_request(f'/2/users/{user_id}/bookmarks', params)
    
    def get_bookmark_folders(self):
        me = self.get_me()
        user_id = me['data']['id']
        return self._api_request(f'/2/users/{user_id}/bookmarks/folders')


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Commands:")
        print("  me                    - Get current user info")
        print("  bookmarks [max]       - Get bookmarks")
        print("  folders               - Get bookmark folders")
        sys.exit(1)
    
    client = XHaruClient()
    command = sys.argv[1]
    
    if command == "me":
        result = client.get_me()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif command == "bookmarks":
        max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        result = client.get_bookmarks(max_results)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif command == "folders":
        result = client.get_bookmark_folders()
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
