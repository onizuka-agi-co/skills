#!/usr/bin/env python3
"""
X API Cache Layer
Reduces API calls by caching responses locally
"""

import json
import hashlib
import time
from pathlib import Path
from datetime import datetime, timezone

# Cache directory
CACHE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "x" / "cache"

# Default TTL (Time To Live) in seconds
DEFAULT_TTL = {
    'user': 86400,        # 24 hours - user info rarely changes
    'tweet': 3600,        # 1 hour - tweets don't change after posting
    'timeline': 300,      # 5 minutes - timeline changes frequently
    'mentions': 300,      # 5 minutes
    'search': 600,        # 10 minutes
}

class XCache:
    def __init__(self, cache_dir=None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, endpoint, params=None):
        """Generate a unique cache key for the request"""
        key_str = endpoint
        if params:
            key_str += json.dumps(params, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key):
        """Get the file path for a cache key"""
        return self.cache_dir / f"{cache_key}.json"
    
    def _get_ttl(self, endpoint):
        """Get TTL for an endpoint"""
        if 'user' in endpoint:
            return DEFAULT_TTL['user']
        elif 'tweets/' in endpoint and 'timeline' not in endpoint:
            return DEFAULT_TTL['tweet']
        elif 'timeline' in endpoint:
            return DEFAULT_TTL['timeline']
        elif 'mentions' in endpoint:
            return DEFAULT_TTL['mentions']
        elif 'search' in endpoint:
            return DEFAULT_TTL['search']
        return 3600  # Default 1 hour
    
    def get(self, endpoint, params=None):
        """Get cached response if available and not expired"""
        cache_key = self._get_cache_key(endpoint, params)
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r') as f:
                cached = json.load(f)
            
            # Check if expired
            ttl = self._get_ttl(endpoint)
            if time.time() - cached['timestamp'] > ttl:
                return None
            
            return cached['data']
        except Exception:
            return None
    
    def set(self, endpoint, data, params=None):
        """Cache a response"""
        cache_key = self._get_cache_key(endpoint, params)
        cache_path = self._get_cache_path(cache_key)
        
        cached = {
            'endpoint': endpoint,
            'params': params,
            'data': data,
            'timestamp': time.time(),
            'cached_at': datetime.now(timezone.utc).isoformat()
        }
        
        with open(cache_path, 'w') as f:
            json.dump(cached, f, indent=2, ensure_ascii=False)
    
    def invalidate(self, endpoint, params=None):
        """Invalidate a specific cache entry"""
        cache_key = self._get_cache_key(endpoint, params)
        cache_path = self._get_cache_path(cache_key)
        
        if cache_path.exists():
            cache_path.unlink()
    
    def clear_all(self):
        """Clear all cache entries"""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
    
    def get_stats(self):
        """Get cache statistics"""
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            'entries': len(cache_files),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2)
        }


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("X API Cache Manager")
        print("\nUsage: python x_cache.py <command>")
        print("\nCommands:")
        print("  stats     - Show cache statistics")
        print("  clear     - Clear all cache entries")
        print("  list      - List all cache entries")
        sys.exit(1)
    
    cache = XCache()
    command = sys.argv[1]
    
    if command == "stats":
        stats = cache.get_stats()
        print(json.dumps(stats, indent=2))
    
    elif command == "clear":
        cache.clear_all()
        print("✅ Cache cleared")
    
    elif command == "list":
        for cache_file in sorted(cache.cache_dir.glob("*.json")):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                age = int(time.time() - data['timestamp'])
                print(f"{cache_file.name}: {data['endpoint']} (age: {age}s)")
            except Exception as e:
                print(f"{cache_file.name}: Error - {e}")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
