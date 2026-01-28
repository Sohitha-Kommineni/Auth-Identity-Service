from fastapi import HTTPException

from app.core.redis import get_redis


class RateLimiter:
    def __init__(self) -> None:
        self.redis = get_redis()

    def hit(self, key: str, limit: int, window_seconds: int) -> None:
        count = self.redis.incr(key)
        if count == 1:
            self.redis.expire(key, window_seconds)
        if count > limit:
            raise HTTPException(status_code=429, detail="Too many requests")
