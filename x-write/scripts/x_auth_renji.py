#!/usr/bin/env python3
"""
X OAuth2 Authentication Helper for Onizuka_Renji
Uses /config/x-filtered-stream/data/ credentials
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

# Onizuka_Renji configuration paths
DATA_DIR = Path("/config/x-filtered-stream/data")
TOKEN_FILE = DATA_DIR / "x-tokens.json"
CLIENT_CREDENTIALS_FILE = DATA_DIR / "x-client-credentials.json"
SESSION_FILE = DATA_DIR / "x-oauth-session.json"

PORT = 8080
REDIRECT_URI = f"http://localhost:{PORT}/callback"
SCOPE = "offline.access tweet.write media.write users.read tweet.read"


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
        pass


def generate_pkce():
    """Generate PKCE code verifier and challenge"""
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode().rstrip('=')
    return code_verifier, code_challenge


def load_credentials():
    """Load client credentials"""
    if not CLIENT_CREDENTIALS_FILE.exists():
        raise FileNotFoundError(f"Client credentials not found: {CLIENT_CREDENTIALS_FILE}")
    
    with open(CLIENT_CREDENTIALS_FILE, 'r') as f:
        return json.load(f)


def save_session(code_verifier, state):
    """Save OAuth session data"""
    session = {
        'code_verifier': code_verifier,
        'state': state,
        'created_at': time.time()
    }
    with open(SESSION_FILE, 'w') as f:
        json.dump(session, f, indent=2)


def load_session():
    """Load OAuth session data"""
    if SESSION_FILE.exists():
        with open(SESSION_FILE, 'r') as f:
            return json.load(f)
    return None


def exchange_code_for_token(code, code_verifier, credentials):
    """Exchange authorization code for access token"""
    basic_auth = base64.b64encode(
        f"{credentials['client_id']}:{credentials['client_secret']}".encode()
    ).decode()
    
    data = urllib.parse.urlencode({
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI,
        'code_verifier': code_verifier
    }).encode()
    
    req = urllib.request.Request(
        'https://api.x.com/2/oauth2/token',
        data=data,
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
    print(f"✅ Tokens saved to {TOKEN_FILE}")


def main():
    print("🔐 X OAuth2 Authentication for Onizuka_Renji")
    print("=" * 50)
    
    credentials = load_credentials()
    print(f"Client ID: {credentials['client_id'][:20]}...")
    
    code_verifier, code_challenge = generate_pkce()
    state = secrets.token_urlsafe(16)
    save_session(code_verifier, state)
    
    auth_url = (
        f"https://twitter.com/i/oauth2/authorize?"
        f"response_type=code&"
        f"client_id={credentials['client_id']}&"
        f"redirect_uri={urllib.parse.quote(REDIRECT_URI)}&"
        f"scope={urllib.parse.quote(SCOPE)}&"
        f"state={state}&"
        f"code_challenge={code_challenge}&"
        f"code_challenge_method=S256"
    )
    
    print(f"\n📱 Opening browser for authentication...")
    print(f"If browser doesn't open, visit this URL:\n{auth_url}\n")
    
    with socketserver.TCPServer(("", PORT), CallbackHandler) as httpd:
        print(f"🌐 Waiting for callback on port {PORT}...")
        webbrowser.open(auth_url)
        
        timeout = 120
        start_time = time.time()
        while time.time() - start_time < timeout:
            httpd.handle_request()
            if CallbackHandler.received_code:
                break
        
        if not CallbackHandler.received_code:
            print("❌ Authentication timed out")
            return 1
        
        print(f"✅ Received authorization code")
        
        session = load_session()
        if not session:
            print("❌ Session data not found")
            return 1
        
        tokens = exchange_code_for_token(
            CallbackHandler.received_code,
            session['code_verifier'],
            credentials
        )
        
        if 'access_token' in tokens:
            save_tokens(tokens)
            print("\n🎉 Authentication successful!")
            print(f"Access token expires in: {tokens.get('expires_in', 'unknown')} seconds")
            return 0
        else:
            print(f"❌ Token exchange failed: {tokens}")
            return 1


if __name__ == "__main__":
    exit(main())
