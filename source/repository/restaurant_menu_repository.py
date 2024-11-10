from typing import Any, Type

from fastapi import Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Base
from database.session_manager import get_session


class RestaurantMenuRepository:

    def __init__(self, session: AsyncSession = Depends(get_session)) -> None:
        self.session = session

    async def create_entity(self, entity_type: Type[Base], **kwargs: Any) -> Base:
        entity = entity_type(**kwargs)
        async with self.session.begin():
            self.session.add(entity)
        await self.session.refresh(entity)
        return entity

    async def get_entity_by_id(self, entity_type: Type[Base], entity_id: str) -> Base | None:
        return await self.session.get(entity_type, entity_id)

    async def get_entities(self, entity_type: Type[Base]) -> list[Base] | list[None]:
        entities = await self.session.scalars(select(entity_type))
        return entities.all()

    async def update_entity(self, entity_type: Type[Base], entity_id: str, **kwargs: Any) -> Base | None:
        async with self.session.begin():
            entity = await self.session.get(entity_type, entity_id)
            for column_name, value in kwargs.items(): setattr(entity, column_name, value)
        await self.session.refresh(entity)
        return entity

    async def delete_entity(self, entity_type: Type[Base], entity_id: str) -> None:
        statement = delete(entity_type).where(entity_type.id == entity_id)
        async with self.session.begin():
            await self.session.execute(statement)
