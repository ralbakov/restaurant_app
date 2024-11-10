import pickle
from dataclasses import dataclass, fields, InitVar

from fastapi import Depends

from database.models import Menu, Submenu, Dish, Base
from database.schemas import Schema
from repository.restaurant_menu_repository import RestaurantMenuRepository
from utils.redis_cache import RedisCache


@dataclass
class EntityCode:
    value: Base | list[Base]

    @property
    def cache_name(self) -> str:
        return f'menu:{self.value.id}:submenu::dish:'


@dataclass
class TargetCode:
    menu: str = ''
    submenu: str = ''
    dish: str = ''
    entity_code: InitVar[EntityCode] | None = None

    def construct_cache_name(self) -> str:
        if self.entity_code:
            attribute = self.entity_code.value.__name__.lower()
            if hasattr(self, attribute):
                setattr(self, attribute, str(self.entity_code.value.id))
        return f'menu:{self.menu}:submenu:{self.submenu}:dish:{self.dish}'


class EntityNotRegistered(ValueError):
    def __init__(self, entity_name: str | None) -> None:
        super().__init__(
            f'Entity "{entity_name.capitalize()}" is not registered.')


class RestaurantMenuService:

    def __init__(self, repository: RestaurantMenuRepository = Depends(), cache: RedisCache = Depends()) -> None:
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

    async def create(
        self,
        entity_name: str,
        creation_schema: Schema,
        target_code: TargetCode | str | None = None,
    ) -> Base:
        entity_type = self._get_entity_type(entity_name)
        creation_schema_as_dict = creation_schema.model_dump()
        if target_code:
            column_to_value = self._get_relation_column_name_to_value(target_code, entity_type)
            creation_schema_as_dict.update(column_to_value)

        entity = await self.repository.create_entity(entity_type, **creation_schema_as_dict)
        entity_code = EntityCode(entity)
        if target_code:
            target_code.entity_code = entity_code
            cache_payload = target_code
        else:
            cache_payload = entity_code

        await self.invalidate_cache(cache_payload)
        return entity

    async def read_one(
            self,
            entity_name: str,
            entity_id: str,
            cache_name: TargetCode | str,
    ) -> Base | None:
        if cache := await self.get_cache(entity_id, cache_name):
            return cache

        entity_type = self._get_entity_type(entity_name)
        if not (entity := await self.repository.get_entity_by_id(entity_type, entity_id)):
            raise ValueError(f'{entity_name} not found')
        await self.invalidate_cache(entity, entity_id, cache_name)
        return entity

    async def update(
            self,
            entity_name: str,
            entity_id: str,
            updation_schema: Schema,
            cache_name: TargetCode | str,
    ) -> Base | None:
        entity_type = self._get_entity_type(entity_name)
        column_to_value = {
            column: value for column, value in updation_schema.model_dump().items() if hasattr(entity_type, column)
        }
        entity = await self.repository.update_entity(entity_type, entity_id, **column_to_value)
        await self.invalidate_cache(entity, entity_id, cache_name)
        return entity

    async def delete(self, entity_name: str, entity_id: str, cache_name: TargetCode | str) -> None:

        entity_type = self._get_entity_type(entity_name)
        await self.repository.delete_entity(entity_type, entity_id)
        await self.delete_cache(cache_name)

    async def read_all(self, entity_name: str, cache_name: TargetCode | str) -> list[Base] | None:
        if cache := await self.get_cache(entity_name, cache_name):
            return cache

        entity_type = self._get_entity_type(entity_name)
        entities =  await self.repository.get_entities(entity_type)
        await self.set_cache(entity_name, entities, cache_name)
        return entities

    async def set_cache(
            self,
            key: str,
            value: Base | list[Base],
            cache_name: str,
    ) -> None:
        value_serialized = self._serialize_pickle(value)
        await self.cache.hset(cache_name, key, value_serialized)

    async def get_cache(
            self,
            key: str,
            cache_name: TargetCode | str,
    ) -> Base | list[Base] | None:
        if isinstance(cache_name, TargetCode):
            cache_name = cache_name.construct_cache_name()
        cache_value = await self.cache.hget(cache_name, key)
        return self._deserialize_pickle(cache_value)

    async def delete_cache(self, cache_name: TargetCode | str) -> None:
        cache_names = self.construct_keys_for_delete_cache(cache_name)
        print(cache_names)
        await self.cache.delete(cache_names)

    async def invalidate_cache(self, cache_payload: TargetCode | EntityCode) -> None:
        if isinstance(cache_payload, EntityCode):
            await self.set_cache(str(cache_payload.value.id), cache_payload.value, cache_payload.cache_name)
        entity_name_to_cache_name = self.construct_entity_name_to_cache_name(cache_payload)
        print(entity_name_to_cache_name)
        for entity_name in self.entity_name_to_entity_type:
            entity_type = self.entity_name_to_entity_type[entity_name]
            entities = await self.repository.get_entities(entity_type)
            if (id_ := getattr(cache_payload, f'{entity_name}_id') != '') and isinstance(cache_payload, TargetCode):
                print(id_)
                entity = await self.repository.get_entity_by_id(entity_type, id_)
                await self.set_cache(id_, entity, cache_payload)
            print(entities)
            cache_payload = entity_name_to_cache_name[entity_name]
            print(cache_payload)
            await self.set_cache(entity_name, entities, cache_payload)

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
    def construct_keys_for_delete_cache(cache_name: TargetCode) -> set[str]:
        print(cache_name)
        pattern = f'menu_id:{cache_name.menu}:submenu_id:'
        menu_key = f'{pattern}:dish_id:'
        submenu_key = f'{pattern}{cache_name.submenu}:dish_id:'
        dish_key = f'{submenu_key}{cache_name.dish}'
        menus = TargetCode().construct_cache_name()
        return {menu_key, submenu_key, dish_key, menus}
    
    @staticmethod
    def construct_entity_name_to_cache_name(cache_name: TargetCode) -> dict[str, str]:
        menu_key = TargetCode().construct_cache_name()
        submenu_key = f'menu_id:{cache_name.menu}:submenu_id:'
        dish_key = f'{submenu_key}{cache_name.submenu}:dish_id:'
        return {
            Menu.__name__.lower(): menu_key,
            Submenu.__name__.lower(): submenu_key,
            Dish.__name__.lower(): dish_key
        }

    @staticmethod
    def _get_relation_column_name_to_value(target_code: TargetCode, entity_type: type[Base]):
        return {
            f'{field.name}_id': getattr(target_code, field.name)
            for field in fields(target_code) if hasattr(entity_type, f'{field.name}_id')
        }