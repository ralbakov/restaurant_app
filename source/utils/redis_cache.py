from redis import asyncio as aioredis

from core.config import settings


class RedisCache:
    redis_connection: aioredis.Redis  = aioredis.from_url(settings.redis_cache.url)

    @classmethod
    async def hset(cls, name: str, key: str, value: bytes) -> None:
        await cls.redis_connection.hset(name, key=key, value=value)
        await cls.redis_connection.expire(name, settings.redis_cache.ttl)

    @classmethod
    async def hget(cls, name: str, key: str) -> bytes:
        return await cls.redis_connection.hget(name, key)

    @classmethod
    async def delete(cls, *names: str) -> None:
        await cls.redis_connection.delete(*names)

    @classmethod
    async def hdel(cls, name: str, *keys: str) -> None:
        await cls.redis_connection.hdel(name,*keys)

    @classmethod
    async def get_keys(cls, pattern: str) -> list[str]:
        return await cls.redis_connection.keys(pattern)
