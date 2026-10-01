import json
import os
import hashlib
from datetime import datetime

class CacheService:
    def __init__(self, cache_dir: str = 'cache'):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    async def get(self, key: str, ttl: int = 86400) -> dict:
        cache_file = self._cache_file(key)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                created = datetime.fromisoformat(data['created_at'])
                if (datetime.now() - created).total_seconds() < ttl:
                    return data['response']
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                return None
        return None

    async def set(self, key: str, response: dict):
        cache_file = self._cache_file(key)
        data = {'response': response, 'created_at': datetime.now().isoformat()}
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _cache_file(self, key: str) -> str:
        filename = hashlib.sha256(key.encode('utf-8')).hexdigest() + '.json'
        return os.path.join(self.cache_dir, filename)
