import pickle
from dataclasses import dataclass, fields, field

from fastapi import Depends, BackgroundTasks
from pydantic import BaseModel

from database.models import Menu, Submenu, Dish, Base
from database.schemas import Schema
from repository.restaurant_repository import RestaurantRepository
from utils.redis_cache import RedisCache


@dataclass
class EntityCode:
    value: Base


@dataclass
class TargetCode:
    entity_name: str
    menu: str = field(default='')
    submenu: str = field(default='')
    dish: str = field(default='')
    entity_code: EntityCode = field(default=None)

    @property
    def entity_name_to_cache_name(self) -> dict[str, str]:
        return {
            'menu': f'menu::submenu::dish:',
            'submenu': f'menu:{self.menu}:submenu::dish:',
            'dish': f'menu:{self.menu}:submenu:{self.submenu}:dish:',
        }

    @classmethod
    def construct_entity_name(cls, schema: type[BaseModel]):
        return cls(schema.__name__.lower())

class EntityNotRegistered(ValueError):
    def __init__(self, entity_name: str | None) -> None:
        super().__init__(f'Entity "{entity_name.capitalize()}" is not registered.')


class RestaurantService:
    def __init__(self, repository: RestaurantRepository = Depends(), cache: RedisCache = Depends()) -> None:
        self.repository = repository
        self.cache = cache
        self.entity_types = [Menu, Submenu, Dish]
        self.entity_name_to_entity_type = self._register_entity()

    def _register_entity(self) -> dict[str, type[Base]]:
        return {entity_type.__name__.lower(): entity_type for entity_type in self.entity_types}

    def _get_entity_type(self, entity_name: str) -> type[Base]:
        try:
            entity_type = self.entity_name_to_entity_type[entity_name]
        except KeyError:
            raise EntityNotRegistered(entity_name)
        return entity_type

    async def create(self, creation_schema: Schema, target_code: TargetCode, task: BackgroundTasks) -> Base:
        entity_type = self._get_entity_type(target_code.entity_name)
        creation_schema_as_dict = creation_schema.model_dump()
        if target_code.menu or target_code.submenu or target_code.dish:
            column_to_value = self._get_relation_column_name_to_value(target_code, entity_type)
            creation_schema_as_dict.update(column_to_value)

        entity = await self.repository.create_entity(entity_type, **creation_schema_as_dict)
        target_code.entity_code = EntityCode(entity)
        task.add_task(self._invalidate_cache, target_code)
        return entity

    async def read_one(self, target_code: TargetCode, task: BackgroundTasks) -> Base:
        entity_name = target_code.entity_name
        entity_id = getattr(target_code, entity_name)
        cache_name = target_code.entity_name_to_cache_name[entity_name]
        if cache := await self.get_cache(entity_id, cache_name):
            return cache

        entity_type = self._get_entity_type(entity_name)
        if not (entity := await self.repository.get_entity_by_id(entity_type, entity_id)):
            raise ValueError(f'{entity_name} not found')

        task.add_task(self.set_cache, entity_id, entity, cache_name)
        return entity

    async def update(self, updation_schema: Schema, target_code: TargetCode, task: BackgroundTasks) -> Base | None:
        entity_name = target_code.entity_name
        entity_id = getattr(target_code, entity_name)
        entity_type = self._get_entity_type(entity_name)
        column_to_value = {
            column: value for column, value in updation_schema.model_dump().items() if hasattr(entity_type, column)
        }
        entity = await self.repository.update_entity(entity_type, entity_id, **column_to_value)
        cache_name = target_code.entity_name_to_cache_name[entity_name]
        task.add_task(self.set_cache,entity_id, entity, cache_name)
        return entity

    async def delete(self, target_code: TargetCode, task: BackgroundTasks) -> None:
        entity_name = target_code.entity_name
        entity_id = getattr(target_code, entity_name)
        entity_type = self._get_entity_type(entity_name)
        await self.repository.delete_entity(entity_type, entity_id)
        task.add_task(self.delete_cache, target_code)

    async def read_all(self, target_code: TargetCode, task: BackgroundTasks) -> list[Base] | None:
        entity_name = target_code.entity_name
        cache_name = target_code.entity_name_to_cache_name[entity_name]
        if cache := await self.get_cache(entity_name, cache_name):
            return cache

        entity_type = self._get_entity_type(entity_name)
        entities =  await self.repository.get_entities(entity_type)
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
        cache_name = target_code.entity_name_to_cache_name[entity_name]
        if not target_code.menu and not target_code.submenu and not target_code.dish:
            return await self._invalidate_cache_entity(entity_name, cache_name, entity=target_code.entity_code.value)

        await self._invalidate_cache_entity(entity_name, cache_name, entity=target_code.entity_code.value)
        if target_code.submenu and not target_code.dish:
            submenu_name = Submenu.__name__.lower()
            submenu_cache_name = target_code.entity_name_to_cache_name[submenu_name]
            await self._invalidate_cache_entity(submenu_name, submenu_cache_name, entity_id=target_code.submenu)

        menu_name = Menu.__name__.lower()
        menu_cache_name = target_code.entity_name_to_cache_name[menu_name]
        return await self._invalidate_cache_entity(menu_name, menu_cache_name, entity_id=target_code.menu)


    async def _invalidate_cache_entity(self,
                                       entity_name: str,
                                       cache_name: str,
                                       entity_id: str = None,
                                       entity: Base = None) -> None:
        entity_type = self.entity_name_to_entity_type[entity_name]
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
        menu_name, submenu_name, dish_name = self.entity_name_to_entity_type.keys()
        menu_cache_name = target_code.entity_name_to_cache_name[menu_name]
        submenu_cache_name = target_code.entity_name_to_cache_name[submenu_name]
        dish_cache_name = target_code.entity_name_to_cache_name[dish_name]
        cache_name_to_key = {menu_cache_name: [target_code.menu, menu_name]}
        if target_code.dish:
            cache_name_to_key.update(
                {
                    dish_cache_name: [target_code.dish, dish_name],
                    submenu_cache_name: [target_code.submenu, submenu_name],
                }
            )

        if target_code.submenu:
            cache_name_to_key.update({dish_cache_name: None, submenu_cache_name: [target_code.submenu, submenu_name]})

        if target_code.menu:
            cache_name_to_key.update({dish_cache_name: None, submenu_cache_name: None})

        return cache_name_to_key

    @staticmethod
    def _get_relation_column_name_to_value(target_code: TargetCode, entity_type: type[Base]):
        return {
            f'{field_.name}_id': getattr(target_code, field_.name)
            for field_ in fields(target_code) if hasattr(entity_type, f'{field_.name}_id')
        }