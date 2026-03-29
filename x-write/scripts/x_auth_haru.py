#!/usr/bin/env python3
"""
X OAuth2 Authentication Helper for hAru_mAki_ch
Uses separate client credentials
"""

import http.server
import socketserver
import urllib.parse
import urllib.request
import json
import webbrowser
import time
import base64
import hashlib
import secrets
from pathlib import Path

# Configuration paths
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "x"
TOKEN_FILE = DATA_DIR / "x-tokens-haru.json"
CLIENT_CREDENTIALS_FILE = DATA_DIR / "x-client-credentials-haru.json"
SESSION_FILE = DATA_DIR / "x-oauth-session-haru.json"

PORT = 8080
REDIRECT_URI = f"http://localhost:{PORT}/callback"
SCOPE = "offline.access tweet.write media.write users.read tweet.read bookmark.read"


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    received_code = None
    received_state = None
    
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/callback':
            params = urllib.parse.parse_qs(parsed.query)
            if 'code' in params:
                CallbackHandler.received_code = params['code'][0]
                if 'state' in params:
                    CallbackHandler.received_state = params['state'][0]
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                html = '''<!DOCTYPE html>
<html>
<head><title>Success</title></head>
<body style="font-family: sans-serif; text-align: center; padding: 50px;">
    <h1 style="color: #4CAF50;">Authentication Successful!</h1>
    <p>You can close this tab now.</p>
</body>
</html>'''
                self.wfile.write(html.encode('utf-8'))
                return
        self.send_response(404)
        self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress logging


def load_credentials():
    """Load client credentials"""
    if not CLIENT_CREDENTIALS_FILE.exists():
        raise FileNotFoundError(f"Client credentials not found: {CLIENT_CREDENTIALS_FILE}")
    
    with open(CLIENT_CREDENTIALS_FILE) as f:
        return json.load(f)


def generate_pkce():
    """Generate PKCE code_verifier and code_challenge"""
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip('=')
    return code_verifier, code_challenge


def save_session(code_verifier, state):
    """Save code_verifier with state (複数セッション対応)"""
    sessions = {}
    if SESSION_FILE.exists():
        with open(SESSION_FILE) as f:
            sessions = json.load(f)
    
    sessions[state] = code_verifier
    
    with open(SESSION_FILE, 'w') as f:
        json.dump(sessions, f, indent=2)


def load_code_verifier(state):
    """Load code_verifier for specific state"""
    if SESSION_FILE.exists():
        with open(SESSION_FILE) as f:
            sessions = json.load(f)
            return sessions.get(state)
    return None


def exchange_code_for_token(code, code_verifier, client_id, client_secret):
    """Exchange authorization code for access token"""
    basic_auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    body = urllib.parse.urlencode({
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'code_verifier': code_verifier
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
        return json.loads(resp.read().decode())


def save_tokens(tokens):
    """Save access tokens"""
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f, indent=2)


def authenticate(timeout=120):
    """
    Perform OAuth2 authentication with automatic callback handling.
    """
    # Load credentials
    creds = load_credentials()
    client_id = creds['client_id']
    client_secret = creds['client_secret']
    
    # Generate PKCE
    code_verifier, code_challenge = generate_pkce()
    state = secrets.token_urlsafe(16)
    save_session(code_verifier, state)
    
    # Generate auth URL
    params = {
        'response_type': 'code',
        'client_id': client_id,
        'redirect_uri': REDIRECT_URI,
        'scope': SCOPE,
        'state': state,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256'
    }
    auth_url = f"https://twitter.com/i/oauth2/authorize?{urllib.parse.urlencode(params)}"
    
    print(f"🔐 Starting OAuth2 authentication for hAru_mAki_ch...")
    print(f"🌐 Opening browser...")
    print(f"📍 Callback: {REDIRECT_URI}")
    
    # Start local server and handle callback
    CallbackHandler.received_code = None
    CallbackHandler.received_state = None
    
    with socketserver.TCPServer(('', PORT), CallbackHandler) as httpd:
        # Open browser
        webbrowser.open(auth_url)
        
        # Wait for callback
        start = time.time()
        while CallbackHandler.received_code is None and (time.time() - start) < timeout:
            httpd.handle_request()
        
        code = CallbackHandler.received_code
        callback_state = CallbackHandler.received_state
        
        if not code:
            raise TimeoutError("Authentication timed out")
        
        print(f"✅ Received authorization code")
        print(f"✅ State: {callback_state}")
        
        # Load code_verifier for this state
        code_verifier = load_code_verifier(callback_state)
        if not code_verifier:
            raise ValueError(f"No code_verifier found for state: {callback_state}")
        
        # Exchange code for token
        try:
            tokens = exchange_code_for_token(code, code_verifier, client_id, client_secret)
            
            # Save tokens
            save_tokens(tokens)
            
            print(f"✅ Token saved to {TOKEN_FILE}")
            print(f"⏱️  Expires in: {tokens.get('expires_in', 7200)} seconds")
            
            return tokens
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            print(f"❌ Token exchange failed: HTTP {e.code}")
            print(f"Error details: {error_body}")
            raise


def main():
    import sys
    
    try:
        tokens = authenticate()
        print()
        print("🎉 Authentication successful!")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
