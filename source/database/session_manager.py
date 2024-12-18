from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import settings
from database.models import Base


engine = create_async_engine(url=settings.db.url, pool_pre_ping=True)


sessionmaker = async_sessionmaker(bind=engine, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with sessionmaker() as session:
        try:
            yield session
        except DBAPIError:
            await session.rollback()
        finally:
            await session.close()


async def init_models() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def close_engine() -> None:
    await engine.dispose()
