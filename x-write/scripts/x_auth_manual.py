#!/usr/bin/env python3
"""
Manual OAuth2 flow for container environments
Step 1: Generate auth URL
Step 2: User authorizes and gets code from redirect URL
Step 3: Exchange code for token
"""

import urllib.parse
import urllib.request
import json
import base64
import hashlib
import secrets
from pathlib import Path

# Configuration paths
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "x"
TOKEN_FILE = DATA_DIR / "x-tokens.json"
CLIENT_CREDENTIALS_FILE = DATA_DIR / "x-client-credentials.json"
SESSION_FILE = DATA_DIR / "x-oauth-session.json"

REDIRECT_URI = "http://localhost:8080/callback"
SCOPE = "offline.access tweet.write media.write users.read tweet.read bookmark.read"


def load_credentials():
    if not CLIENT_CREDENTIALS_FILE.exists():
        raise FileNotFoundError(f"Client credentials not found: {CLIENT_CREDENTIALS_FILE}")
    with open(CLIENT_CREDENTIALS_FILE) as f:
        return json.load(f)


def generate_pkce():
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip('=')
    return code_verifier, code_challenge


def save_session(code_verifier, state):
    with open(SESSION_FILE, 'w') as f:
        json.dump({'code_verifier': code_verifier, 'state': state}, f)


def load_session():
    if SESSION_FILE.exists():
        with open(SESSION_FILE) as f:
            return json.load(f)
    return None


def generate_auth_url():
    creds = load_credentials()
    client_id = creds['client_id']
    
    code_verifier, code_challenge = generate_pkce()
    state = secrets.token_urlsafe(16)
    save_session(code_verifier, state)
    
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
    
    print("=" * 60)
    print("STEP 1: Open this URL in your browser:")
    print("=" * 60)
    print(auth_url)
    print("=" * 60)
    print()
    print("After authorization, you'll be redirected to localhost.")
    print("Copy the 'code' parameter from the redirect URL.")
    print()
    print("Example redirect URL:")
    print(f"{REDIRECT_URI}?code=XXXXXXXX&state=YYYYYYYY")
    print()
    print("Then run:")
    print("  python x_auth_manual.py exchange <code>")


def exchange_code(code):
    session = load_session()
    if not session:
        raise Exception("No session found. Run 'python x_auth_manual.py url' first.")
    
    code_verifier = session['code_verifier']
    
    creds = load_credentials()
    client_id = creds['client_id']
    client_secret = creds['client_secret']
    
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
    
    try:
        with urllib.request.urlopen(req) as resp:
            tokens = json.loads(resp.read().decode())
        
        with open(TOKEN_FILE, 'w') as f:
            json.dump(tokens, f, indent=2)
        
        print("=" * 60)
        print("✅ Authentication successful!")
        print("=" * 60)
        print(f"Scope: {tokens.get('scope')}")
        print(f"Token saved to: {TOKEN_FILE}")
        print()
        
        return tokens
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"❌ Error: {e.code}")
        print(error_body)
        return None


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Manual OAuth2 Flow")
        print()
        print("Usage:")
        print("  python x_auth_manual.py url        - Generate auth URL")
        print("  python x_auth_manual.py exchange <code>  - Exchange code for token")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "url":
        generate_auth_url()
    elif command == "exchange":
        if len(sys.argv) < 3:
            print("Usage: python x_auth_manual.py exchange <code>")
            sys.exit(1)
        code = sys.argv[2]
        exchange_code(code)
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
