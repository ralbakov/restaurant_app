import pickle
from dataclasses import dataclass, fields, InitVar

from fastapi import Depends

from database.models import Menu, Submenu, Dish, Base
from database.schemas import Schema
from repository.restaurant_menu_repository import RestaurantMenuRepository
from utils.redis_cache import RedisCache


@dataclass
class RedisCacheName:
    menu_id: str = ''
    submenu_id: str = ''
    dish_id: str = ''
    payload: InitVar[dict] = None

    def __post_init__(self, payload: dict[str, str]) -> None:
        if payload:
            for column, value in payload.items(): setattr(self, column, value)

    def construct_name(self) -> str:
        return f'menu_id:{self.menu_id}:submenu_id:{self.submenu_id}:dish_id:{self.dish_id}'

    def get_column_to_value(self) -> dict[str, str]:
        return {field.name: getattr(self, field.name) for field in fields(self) if getattr(self, field.name) != ''}


class EntityNotRegistered(ValueError):
    def __init__(self, entity_name: str | None) -> None:
        super().__init__(
            f'Entity "{entity_name.capitalize()}" is not registered.')


class RestaurantMenuService:

    def __init__(self, repository: RestaurantMenuRepository = Depends(), cache: RedisCache = Depends()) -> None:
        self.repository = repository
        self.cache = cache
        self.entities_type = [Menu, Submenu, Dish]
        self.entity_name_to_entity_type = self._register_entity()

    def _register_entity(self) -> dict[str, type[Base]]:
        return {entity_type.__name__.lower(): entity_type for entity_type in self.entities_type}

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
        cache_name: RedisCacheName | str | None = None,
    ) -> Base:
        entity_type = self._get_entity_type(entity_name)
        creation_schema_as_dict = creation_schema.model_dump()
        column_to_value: dict | None = None
        if cache_name:
            column_to_value = cache_name.get_column_to_value()
            creation_schema_as_dict.update(
                {column: column_to_value[column] for column in column_to_value if hasattr(entity_type, column)}
            )

        entity = await self.repository.create_entity(entity_type, **creation_schema_as_dict)
        entity_name_to_id = {f'{entity_name}_id': str(entity.id)}
        if column_to_value:
            column_to_value.update(entity_name_to_id)
        else:
            column_to_value = entity_name_to_id
        await self.invalidate_cache(entity, str(entity.id), RedisCacheName(payload=column_to_value))
        return entity

    async def read_one(
            self,
            entity_name: str,
            entity_id: str,
            cache_name: RedisCacheName | str,
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
            cache_name: RedisCacheName | str,
    ) -> Base | None:
        entity_type = self._get_entity_type(entity_name)
        column_to_value = {
            column: value for column, value in updation_schema.model_dump().items() if hasattr(entity_type, column)
        }
        entity = await self.repository.update_entity(entity_type, entity_id, **column_to_value)
        await self.invalidate_cache(entity, entity_id, cache_name)
        return entity

    async def delete(self, entity_name: str, entity_id: str, cache_name: RedisCacheName | str) -> None:

        entity_type = self._get_entity_type(entity_name)
        await self.repository.delete_entity(entity_type, entity_id)
        await self.delete_cache(cache_name)

    async def read_all(self, entity_name: str, cache_name: RedisCacheName | str) -> list[Base] | None:
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
            cache_name: RedisCacheName | str,
    ) -> None:
        if isinstance(cache_name, RedisCacheName):
            cache_name = cache_name.construct_name()
        value_serialized = self._serialize_pickle(value)
        await self.cache.upsert(cache_name, key, value_serialized)

    async def get_cache(
            self,
            key: str,
            cache_name: RedisCacheName | str,
    ) -> Base | list[Base] | None:
        if isinstance(cache_name, RedisCacheName):
            cache_name = cache_name.construct_name()
        cache_value = await self.cache.get(cache_name, key)
        return self._deserialize_pickle(cache_value)

    async def delete_cache(self, cache_name: RedisCacheName | str) -> None:
        cache_names = self.construct_keys_for_delete_cache(cache_name)
        print(cache_names)
        await self.cache.delete(cache_names)

    async def invalidate_cache(
            self,
            entity: Base,
            entity_id: str,
            cache_name: RedisCacheName | str,
    ) -> None:
        await self.set_cache(entity_id, entity, cache_name)
        entity_name_to_cache_name = self.construct_entity_name_to_cache_name(cache_name)
        print(entity_name_to_cache_name)
        for entity_name in self.entity_name_to_entity_type:
            entity_type = self.entity_name_to_entity_type[entity_name]
            entities = await self.repository.get_entities(entity_type)
            if (id_ := getattr(cache_name, f'{entity_name}_id') != '') and isinstance(cache_name, RedisCacheName):
                print(id_)
                entity = await self.repository.get_entity_by_id(entity_type, id_)
                await self.set_cache(id_, entity, cache_name)
            print(entities)
            cache_name = entity_name_to_cache_name[entity_name]
            print(cache_name)
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

    @staticmethod
    def construct_keys_for_delete_cache(cache_name: RedisCacheName) -> set[str]:
        print(cache_name)
        pattern = f'menu_id:{cache_name.menu_id}:submenu_id:'
        menu_key = f'{pattern}:dish_id:'
        submenu_key = f'{pattern}{cache_name.submenu_id}:dish_id:'
        dish_key = f'{submenu_key}{cache_name.dish_id}'
        menus = RedisCacheName().construct_name()
        return {menu_key, submenu_key, dish_key, menus}
    
    @staticmethod
    def construct_entity_name_to_cache_name(cache_name: RedisCacheName) -> dict[str, str]:
        menu_key = RedisCacheName().construct_name()
        submenu_key = f'menu_id:{cache_name.menu_id}:submenu_id:'
        dish_key = f'{submenu_key}{cache_name.submenu_id}:dish_id:'
        return {
            Menu.__name__.lower(): menu_key,
            Submenu.__name__.lower(): submenu_key,
            Dish.__name__.lower(): dish_key
        }