# rate_limit.py
import os

try:
    import redis
except Exception:
    redis = None

REDIS_URL = os.getenv("REDIS_URL")

_r = None
if redis and REDIS_URL:
    try:
        _r = redis.from_url(REDIS_URL, decode_responses=True)
        _r.ping()
    except Exception:
        _r = None

def allow(user_id: int, action: str, limit: int = 3, ttl: int = 10) -> bool:
    # If Redis not configured/working, don't block users
    if _r is None:
        return True

    bucket = f"rl:{action}:{user_id}"
    n = _r.incr(bucket)
    if n == 1:
        _r.expire(bucket, ttl)
    return n <= limit
