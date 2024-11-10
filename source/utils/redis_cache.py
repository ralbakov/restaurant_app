from redis import asyncio as aioredis

from core.config import settings


# StrictVersion = importlib.reload(sys.modules['dist']).dist


class RedisCache:
    redis_connection: aioredis.Redis  = aioredis.from_url(settings.redis_cache.url)

    @classmethod
    async def upsert(cls, name: str, key: str, value: bytes) -> None:
        await cls.redis_connection.hset(name, key=key, value=value)

    @classmethod
    async def get(cls, name: str, key: str) -> bytes:
        return await cls.redis_connection.hget(name, key)

    @classmethod
    async def delete(cls, names: set[str]) -> None:
        await cls.redis_connection.delete(*names)

    @classmethod
    async def get_keys(cls, name: str, match: str) -> list[str]:
        return await cls.redis_connection.hscan(name, match=match)
