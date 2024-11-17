from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import settings
from database.models import Base


class SessionManager:
    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker[AsyncSession] | None = None
        self.init()
    
    def init(self) -> None:
        self._engine = create_async_engine(url=settings.db.url, pool_pre_ping=True)
        self._sessionmaker = async_sessionmaker(bind=self._engine, expire_on_commit=False)
    
    async def close(self) -> None:
        if self._engine is None:
            return
        await self._engine.dispose()
        self._engine = None
        self._sessionmaker = None

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if not self._sessionmaker:
            raise IOError("SessionManager is not initialized")
        session = self._sessionmaker()
        try:
            yield session
        except Exception as error:
            await session.rollback()
            raise error
        finally:
            await session.close()

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise IOError("SessionManager is not initialized")
        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise
            finally:
                await connection.close()


async def init_models() -> None:
    engine = create_async_engine(url=settings.db.url)
    async with engine.connect() as connection:
        async with connection.begin():
            await connection.run_sync(Base.metadata.create_all)
