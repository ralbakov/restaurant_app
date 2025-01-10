import pickle
from dataclasses import dataclass, fields
from enum import Enum
from typing import Annotated

from fastapi import BackgroundTasks, Depends

from database.models import Menu, Submenu, Dish, Base
from database.redis_cache import RedisCache
from database.schemas import BaseSchema
from repository.restaurant_repository import RestaurantRepository


class Entity(Enum):
    MENU = Menu
    SUBMENU = Submenu
    DISH = Dish


ENTITY_NAME_TO_ENTITY_TYPE = {entity.value.__name__: entity.value for entity in Entity}


@dataclass
class TargetCode:
    entity_name: str
    menu_id: str = ''
    submenu_id: str = ''
    dish_id: str = ''
    entity: Base | None = None
    kwargs: dict | None = None

    @property
    def get_entity_id(self) -> str:
        return getattr(self, f'{self.entity_name.lower()}_id')

    @classmethod
    def get_target(cls, tag: str) -> 'TargetCode':
        return cls(tag)


class RestaurantService:
    def __init__(self,
                 repository: Annotated[RestaurantRepository, Depends(RestaurantRepository)],
                 cache: Annotated[RedisCache, Depends(RedisCache)]) -> None:
        self.repository = repository
        self.cache = cache

    async def create(self, schema: BaseSchema, target_code: TargetCode, task: BackgroundTasks) -> Base:
        entity_type, entity_name, _ = self._construct_entity_param(target_code)
        schema_as_dict = schema.model_dump()
        if target_code.menu_id or target_code.submenu_id or target_code.dish_id:
            kwargs = self._get_relation_column_name_to_value(target_code, entity_type)
            schema_as_dict.update(kwargs)
            target_code.kwargs = kwargs

        entity = await self.repository.create_entity(entity_type, **schema_as_dict)
        target_code.entity = entity
        task.add_task(self.set_cache, target_code)
        return entity

    async def read_one(self, target_code: TargetCode, task: BackgroundTasks) -> Base:
        entity_type, entity_name, entity_id = self._construct_entity_param(target_code)
        cache_name = self._construct_cache_name(entity_name, target_code)
        if cache := await self.get_cache(entity_id, cache_name):
            return cache

        if not (entity := await self.repository.get_entity_by_id(entity_type, entity_id)):
            raise ValueError(f'{entity_name.lower()} not found')

        task.add_task(self._set_cache, entity_id, entity, cache_name)
        return entity

    async def update(self, schema: BaseSchema, target_code: TargetCode, task: BackgroundTasks) -> Base | None:
        entity_type, entity_name, entity_id = self._construct_entity_param(target_code)
        column_to_value = {
            column: value for column, value in schema.model_dump().items() if hasattr(entity_type, column)
        }
        entity = await self.repository.update_entity(entity_type, entity_id, **column_to_value)
        if entity is None:
            raise ValueError(f'{entity_name.lower()} not found')

        target_code.entity = entity
        task.add_task(self.update_cache, target_code)
        return entity

    async def delete(self, target_code: TargetCode, task: BackgroundTasks) -> None:
        entity_type, _, entity_id = self._construct_entity_param(target_code)
        await self.repository.delete_entity(entity_type, entity_id)
        task.add_task(self.delete_cache, target_code)

    async def read_all(self, target_code: TargetCode, task: BackgroundTasks) -> list[Base] | None:
        entity_type, entity_name, _ = self._construct_entity_param(target_code)
        cache_name = self._construct_cache_name(entity_name, target_code)
        if cache := await self.get_cache(entity_name, cache_name):
            return cache

        kwargs = self._get_relation_column_name_to_value(target_code, entity_type)
        entities =  await self.repository.get_entities(entity_type, **kwargs)
        if entities:
            task.add_task(self._set_cache, entity_name, entities, cache_name)
        return entities

    async def _set_cache(self, key: str, value: Base | list[Base], cache_name: str) -> None:
        value_serialized = self._serialize_pickle(value)
        await self.cache.hset(cache_name, key, value_serialized)

    async def get_cache(self, key: str, cache_name: str,) -> Base | list[Base] | None:
        cache_value = await self.cache.hget(cache_name, key)
        return self._deserialize_pickle(cache_value)

    async def delete_cache(self, target_code: TargetCode) -> None:
        cache_name, keys, pattern = self._construct_param_for_delete_cache(target_code)
        await self.cache.hdel(cache_name, *keys)
        keys = await self.cache.get_keys(pattern) if pattern else None
        await self.cache.delete(*keys) if keys else None
        await self.set_cache_entities(target_code)

    async def set_cache(self, target_code: TargetCode) -> None:
        cache_name = self._construct_cache_name(target_code.entity_name, target_code)
        await self._set_cache(str(target_code.entity.id), target_code.entity, cache_name)
        entity_type = ENTITY_NAME_TO_ENTITY_TYPE[target_code.entity_name]
        if target_code.kwargs:
            entities = await self.repository.get_entities(entity_type, **target_code.kwargs)
        else:
            entities = await self.repository.get_entities(entity_type)
        await self._set_cache(target_code.entity_name, entities, cache_name)
        await self.set_cache_entities(target_code)

    async def update_cache(self, target_code: TargetCode) -> None:
        cache_name = self._construct_cache_name(target_code.entity_name, target_code)
        await self._set_cache(str(target_code.entity.id), target_code.entity, cache_name)
        menu, submenu, dish = ENTITY_NAME_TO_ENTITY_TYPE.keys()
        if target_code.entity_name == menu:
            entities, cache_name = await self._construct_param_for_update_cache(target_code)
        elif target_code.entity_name == submenu:
            entities, cache_name = await self._construct_param_for_update_cache(target_code, menu_id=target_code.menu_id)
        else:
            entities, cache_name = await self._construct_param_for_update_cache(target_code,
                                                                                submenu_id=target_code.submenu_id)
        return await self._set_cache(target_code.entity_name, entities, cache_name)

    async def _construct_param_for_update_cache(self,
                                                target_code: TargetCode,
                                                **kwargs) -> tuple[list[Base | None], str]:
        entities = await self.repository.get_entities(ENTITY_NAME_TO_ENTITY_TYPE[target_code.entity_name], **kwargs)
        cache_name = self._construct_cache_name(target_code.entity_name, target_code)
        return entities, cache_name

    async def set_cache_entities(self, target_code: TargetCode) -> None:
        menu, submenu, dish = ENTITY_NAME_TO_ENTITY_TYPE.keys()
        if target_code.entity_name == menu:
            return

        if target_code.entity_name == dish:
            await self._set_cache_entities(
                submenu,
                ENTITY_NAME_TO_ENTITY_TYPE[submenu],
                target_code.submenu_id,
                target_code,
                menu_id=target_code.menu_id
            )

        await self._set_cache_entities(
            menu,
            ENTITY_NAME_TO_ENTITY_TYPE[menu],
            target_code.menu_id,
            target_code
        )

    async def _set_cache_entities(self,
                                  entity_name: str,
                                  entity_type: type[Base],
                                  entity_id: str,
                                  target_code: TargetCode,
                                  **kwargs) -> None:
        entity = await self.repository.get_entity_by_id(entity_type, entity_id)
        entities = await self.repository.get_entities(entity_type, **kwargs)
        cache_name = self._construct_cache_name(entity_name, target_code)
        await self._set_cache(entity_id, entity, cache_name)
        await self._set_cache(entity_name, entities, cache_name)

    @staticmethod
    def _serialize_pickle(entity: Base) -> bytes:
        return pickle.dumps(entity, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def _deserialize_pickle(value: bytes) -> Base | list[Base] | None:
        try:
            return pickle.loads(value)
        except TypeError:
            return None

    @staticmethod
    def _construct_param_for_delete_cache(target_code: TargetCode) -> tuple[str, tuple[str, ...], str]:
        menu, submenu, dish = ENTITY_NAME_TO_ENTITY_TYPE.keys()
        if target_code.entity_name == menu:
            cache_name = f'{menu}::{submenu}::{dish}:'
            keys = (menu, target_code.menu_id)
            pattern = f'{menu}:{target_code.menu_id}:{submenu}:*'
        elif target_code.entity_name == submenu:
            cache_name = f'{menu}:{target_code.menu_id}:{submenu}::{dish}:'
            keys = (submenu, target_code.submenu_id)
            pattern = f'{menu}:{target_code.menu_id}:{submenu}:{target_code.submenu_id}:{dish}:'
        else:
            cache_name = f'{menu}:{target_code.menu_id}:{submenu}:{target_code.submenu_id}:{dish}:'
            keys = (dish, target_code.dish_id)
            pattern = ''
        return cache_name, keys, pattern

    @staticmethod
    def _get_relation_column_name_to_value(target_code: TargetCode, entity_type: type[Base]) -> dict[str, str]:
        return {
            field.name: getattr(target_code, field.name) for field in fields(target_code)
            if hasattr(entity_type, field.name)
        }

    @staticmethod
    def _construct_entity_param(target_code: TargetCode) -> tuple[type[Base], str, str]:
        return ENTITY_NAME_TO_ENTITY_TYPE[target_code.entity_name], target_code.entity_name, target_code.get_entity_id

    @staticmethod
    def _construct_cache_name(entity_name: str, target_code: TargetCode) -> str:
        menu, submenu, dish = ENTITY_NAME_TO_ENTITY_TYPE.keys()
        if entity_name == menu:
            cache_name = f'{menu}::{submenu}::{dish}:'
        elif entity_name == submenu:
            cache_name = f'{menu}:{target_code.menu_id}:{submenu}::{dish}:'
        else:
            cache_name = f'{menu}:{target_code.menu_id}:{submenu}:{target_code.submenu_id}:{dish}:'
        return cache_name
