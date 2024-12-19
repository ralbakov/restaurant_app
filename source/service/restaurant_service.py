import pickle
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import Annotated

from fastapi import BackgroundTasks, Depends

from database.models import Menu, Submenu, Dish, Base
from database.schemas import BaseSchema
from repository.restaurant_repository import RestaurantRepository
from utils.redis_cache import RedisCache


class Entity(Enum):
    MENU = Menu
    SUBMENU = Submenu
    DISH = Dish


ENTITY_NAME_TO_ENTITY_TYPE = {entity.value.__name__: entity.value for entity in Entity}


@dataclass
class EntityCode:
    value: Base


@dataclass
class TargetCode:
    entity_name: str
    menu_id: str = field(default='')
    submenu_id: str = field(default='')
    dish_id: str = field(default='')
    entity_code: EntityCode = field(default=None)

    @property
    def get_entity_id(self) -> str:
        attr_name = self.entity_name.lower() + '_id'
        return getattr(self, attr_name)

    @classmethod
    def get_target(cls, tag: str) -> 'TargetCode':
        return cls(tag)

    @classmethod
    def get_field_names(cls) -> tuple[str, ...]:
        return tuple(field_.name for field_ in fields(cls))


class RestaurantService:
    def __init__(self,
                 repository: Annotated[RestaurantRepository, Depends(RestaurantRepository)],
                 cache: Annotated[RedisCache, Depends(RedisCache)]) -> None:
        self.repository = repository
        self.cache = cache

    async def create(self, schema: BaseSchema, target_code: TargetCode, task: BackgroundTasks) -> Base:
        entity_type, *_ = self._construct_entity_param(target_code)
        schema_as_dict = schema.model_dump()
        if target_code.menu_id or target_code.submenu_id or target_code.dish_id:
            column_to_value = self._get_relation_column_name_to_value(target_code, entity_type)
            schema_as_dict.update(column_to_value)

        entity = await self.repository.create_entity(entity_type, **schema_as_dict)
        target_code.entity_code = EntityCode(entity)
        task.add_task(self._invalidate_cache, target_code)
        return entity

    async def read_one(self, target_code: TargetCode, task: BackgroundTasks) -> Base:
        entity_type, entity_name, entity_id = self._construct_entity_param(target_code)
        cache_name = self._entity_name_to_cache_name(target_code)[entity_name]
        if cache := await self.get_cache(entity_id, cache_name):
            return cache

        if not (entity := await self.repository.get_entity_by_id(entity_type, entity_id)):
            raise ValueError(f'{entity_name.lower()} not found')

        task.add_task(self.set_cache, entity_id, entity, cache_name)
        return entity

    async def update(self, schema: BaseSchema, target_code: TargetCode, task: BackgroundTasks) -> Base | None:
        entity_type, _, entity_id = self._construct_entity_param(target_code)
        column_to_value = {
            column: value for column, value in schema.model_dump().items() if hasattr(entity_type, column)
        }
        entity = await self.repository.update_entity(entity_type, entity_id, **column_to_value)
        target_code.entity_code = EntityCode(entity)
        task.add_task(self._invalidate_cache,target_code)
        return entity

    async def delete(self, target_code: TargetCode, task: BackgroundTasks) -> None:
        entity_type, _, entity_id = self._construct_entity_param(target_code)
        await self.repository.delete_entity(entity_type, entity_id)
        task.add_task(self.delete_cache, target_code)

    async def read_all(self, target_code: TargetCode, task: BackgroundTasks) -> list[Base] | None:
        entity_type, entity_name, _ = self._construct_entity_param(target_code)
        cache_name = self._entity_name_to_cache_name(target_code)[entity_name]
        if cache := await self.get_cache(entity_name, cache_name):
            return cache

        kwargs = self._get_relation_column_name_to_value(target_code, entity_type)
        entities =  await self.repository.get_entities(entity_type, **kwargs)
        if entities:
            task.add_task(self.set_cache, entity_name, entities, cache_name)
        return entities

    async def set_cache(self, key: str, value: Base | list[Base], cache_name: str) -> None:
        value_serialized = self._serialize_pickle(value)
        await self.cache.hset(cache_name, key, value_serialized)

    async def get_cache(self, key: str, cache_name: str,) -> Base | list[Base] | None:
        cache_value = await self.cache.hget(cache_name, key)
        return self._deserialize_pickle(cache_value)

    async def delete_cache(self, target_code: TargetCode | str) -> None:
        cache_name_to_key = self._construct_cache_name_to_key_for_delete_cache(target_code)
        for cache_name, keys in cache_name_to_key.items():
            await self.cache.hdel(cache_name, *keys) if keys else await self.cache.delete(cache_name)

    async def _invalidate_cache(self, target_code: TargetCode) -> None:
        entity_name = target_code.entity_name
        entity_name_to_cache_name = self._entity_name_to_cache_name(target_code)
        cache_name = entity_name_to_cache_name[entity_name]
        menu_name, submenu_name, dish_name = ENTITY_NAME_TO_ENTITY_TYPE.keys()
        if not target_code.menu_id and not target_code.submenu_id and not target_code.dish_id:
            return await self._invalidate_cache_entity(entity_name, cache_name, entity=target_code.entity_code.value)

        await self._invalidate_cache_entity(entity_name, cache_name, entity=target_code.entity_code.value)
        if target_code.submenu_id and not target_code.dish_id:
            submenu_cache_name = entity_name_to_cache_name[submenu_name]
            await self._invalidate_cache_entity(submenu_name, submenu_cache_name, entity_id=target_code.submenu_id)

        menu_cache_name = entity_name_to_cache_name[menu_name]
        return await self._invalidate_cache_entity(menu_name, menu_cache_name, entity_id=target_code.menu_id)


    async def _invalidate_cache_entity(self,
                                       entity_name: str,
                                       cache_name: str,
                                       entity_id: str = None,
                                       entity: Base = None) -> None:
        entity_type = ENTITY_NAME_TO_ENTITY_TYPE[entity_name]
        if entity_id:
            entity = await self.repository.get_entity_by_id(entity_type, entity_id)
        else:
            entity_id = str(entity.id)
        await self.set_cache(entity_id, entity, cache_name)
        entities = await self.repository.get_entities(entity_type)
        await self.set_cache(entity_name, entities, cache_name)


    @staticmethod
    def _serialize_pickle(entity: Base) -> bytes:
        return pickle.dumps(entity, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def _deserialize_pickle(value: bytes) -> Base | list[Base] | None:
        try:
            return pickle.loads(value)
        except TypeError:
            return None

    def _construct_cache_name_to_key_for_delete_cache(self, target_code: TargetCode) -> dict[str, str | None]:
        menu_name, submenu_name, dish_name = ENTITY_NAME_TO_ENTITY_TYPE.keys()
        entity_name_to_cache_name = self._entity_name_to_cache_name(target_code)
        menu_cache_name = entity_name_to_cache_name[menu_name]
        submenu_cache_name = entity_name_to_cache_name[submenu_name]
        dish_cache_name = entity_name_to_cache_name[dish_name]
        cache_name_to_key = {menu_cache_name: [target_code.menu_id, menu_name]}
        if target_code.dish_id:
            cache_name_to_key.update(
                {
                    dish_cache_name: [target_code.dish_id, dish_name],
                    submenu_cache_name: [target_code.submenu_id, submenu_name],
                }
            )

        if target_code.submenu_id:
            cache_name_to_key.update(
                {dish_cache_name: None, submenu_cache_name: [target_code.submenu_id, submenu_name]}
            )

        if target_code.menu_id:
            cache_name_to_key.update({dish_cache_name: None, submenu_cache_name: None})
        return cache_name_to_key

    @staticmethod
    def _get_relation_column_name_to_value(target_code: TargetCode, entity_type: type[Base]) -> dict[str, str]:
        return {
            name: getattr(target_code, name) for name in target_code.get_field_names() if hasattr(entity_type, name)
        }

    @staticmethod
    def _construct_entity_param(target_code: TargetCode) -> tuple[type[Base], str, str]:
        entity_name = target_code.entity_name
        entity_id = target_code.get_entity_id
        entity_type = ENTITY_NAME_TO_ENTITY_TYPE[entity_name]
        return entity_type, entity_name, entity_id

    @staticmethod
    def _entity_name_to_cache_name(target_code: TargetCode) -> dict[str, str]:
        menu, submenu, dish = ENTITY_NAME_TO_ENTITY_TYPE.keys()
        return {
            f'{menu}': f'{menu}::{submenu}::{dish}:',
            f'{submenu}': f'{menu}:{target_code.menu_id}:{submenu}::{dish}:',
            f'{dish}': f'{menu}:{target_code.menu_id}:{submenu}:{target_code.submenu_id}:{dish}:',
        }
