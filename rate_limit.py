from __future__ import annotations
import time
from typing import Optional
import redis
from config import settings

_r: Optional[redis.Redis] = None

def redis_client() -> Optional[redis.Redis]:
    global _r
    if not settings.REDIS_URL:
        return None
    if _r is None:
        _r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _r

def allow(user_id: int, key: str, window_sec: int = 2, limit: int = 3) -> bool:
    r = redis_client()
    if not r:
        return True
    now = int(time.time())
    bucket = f"rl:{key}:{user_id}:{now//window_sec}"
    n = r.incr(bucket)
    if n == 1:
        r.expire(bucket, window_sec + 1)
    return n <= limit
