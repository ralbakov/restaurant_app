from typing import Any, Annotated

from fastapi import Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Base
from database.session_manager import get_session


# from sqlalchemy.dialects.postgresql import insert


class RestaurantRepository:
    def __init__(self, session: Annotated[AsyncSession, Depends(get_session)]) -> None:
        self._session = session

    async def create_entity(self, entity_type: type[Base], **kwargs: Any) -> Base:
        entity = entity_type(**kwargs)
        async with self._session as session:
            session.add(entity)
            await session.commit()
            await session.refresh(entity)
            return entity

    async def get_entity_by_id(self, entity_type: type[Base], entity_id: str) -> Base | None:
        async with self._session as session:
            return await session.get(entity_type, entity_id)

    async def get_entities(self, entity_type: type[Base], **kwargs: str) -> list[Base] | list[None]:
        select_entity = select(entity_type)
        if kwargs:
            where_clause = [getattr(entity_type, name) == value for name, value in kwargs.items()]
            select_entity = select_entity.where(*where_clause)
        async with self._session as session:
            return (await session.scalars(select_entity)).all()

    async def update_entity(self, entity_type: type[Base], entity_id: str, **kwargs: Any) -> Base | None:
        entity = entity_type(**kwargs)
        # statement = insert(entity_type).values(**entity.as_dict).on_conflict_do_update
        async with self._session as session:
            entity = await session.get(entity_type, entity_id)
            for column_name, value in kwargs.items(): setattr(entity, column_name, value)
            await session.commit()
            await session.refresh(entity)
            return entity

    async def delete_entity(self, entity_type: type[Base], entity_id: str) -> None:
        statement = delete(entity_type).where(entity_type.id == entity_id)
        async with self._session as session:
            await session.execute(statement)
            await session.commit()
