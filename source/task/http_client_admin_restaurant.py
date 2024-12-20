import asyncio
import hashlib
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any, IO, TypeVar
from uuid import UUID

import httpx

from core.config import settings
from database.schemas import Menu, Submenu, Dish, BaseSchema
from task.abstract_http_client import AbstractHttpClient
from task.parser_xlsx_service import RestaurantMenu, ParserXlsxService


EntityFromExcel = TypeVar("EntityFromExcel", Menu, Submenu, Dish)


class HttpClientAdminRestaurant(AbstractHttpClient):
    def __init__(self):
        self.base_url: str = f'http://{settings.url.host}:{settings.url.host}'
        self.hash_file: str | None = None
        self.file: IO | None = None

    @property
    @asynccontextmanager
    async def get_client(self):
        client = httpx.AsyncClient(base_url=self.base_url).get()
        try:
            yield client
        finally:
            await client.aclose()

    async def get(self, url: str) -> Any:
        async with self.get_client as client:
            response = await client.get(url)
            if response.status != 200:
                raise ValueError('not found')
            return response.json()

    async def post(self, url: str, json: str) -> Any:
        async with self.get_client as client:
            return (await client.post(url, json=json)).json()

    async def put(self, url: str, json: str) -> Any:
        async with self.get_client as client:
            return (await client.put(url, json=json)).json()

    async def delete(self, url: str) -> None:
        async with self.get_client as client:
            await client.delete(url)

    async def load_restaurant_menu_in_db(self, restaurant_menu: RestaurantMenu) -> None:
        menu_ids_from_db = set(await self.get_entity_ids(settings.url.target_menus))
        if not menu_ids_from_db:
            return await self.post_entity(restaurant_menu)
        menu_ids_from_excel = set(map(str, restaurant_menu.menu))
        difference_ids = menu_ids_from_db - menu_ids_from_excel
        if difference_ids:
            await self.delete_difference_ids(difference_ids, settings.url.target_menu_id)
            menu_ids_from_db.difference_update(difference_ids)
        await self.update_entities(menu_ids_from_db, Menu, settings.url.target_menu_id, restaurant_menu.menu)
        difference_ids = menu_ids_from_excel - menu_ids_from_db
        if difference_ids:
            await self.post_difference_ids(difference_ids, settings.url.target_menus, restaurant_menu.menu)
        menu_id_to_submenu_ids = defaultdict(set)
        for menu_id in menu_ids_from_db:
            submenu_ids = set(await self.get_entity_ids(settings.url.target_submenus.format(menu_id)))
            menu_id_to_submenu_ids[menu_id].update(submenu_ids)
            await self.update_entities(submenu_ids,
                                       Submenu,
                                       settings.url.target_submenu_id.format(target_menu_id=menu_id),
                                       restaurant_menu.submenu)

        pass


    async def post_entity(self, restaurant_menu: RestaurantMenu) -> None:
        for menu in restaurant_menu.menu.values():
            await self.post(settings.url.target_menus, menu.model_dump_json())
        submenu_id_to_menu_id = {}
        for submenu in restaurant_menu.submenu.values():
            menu_id = str(submenu.menu_id)
            await self.post(
                settings.url.target_submenus.format(target_menu_id=menu_id),
                submenu.model_dump_json(),
            )
            submenu_id_to_menu_id[submenu.id] = menu_id
        for dish in restaurant_menu.dish.values():
            submenu_id = str(dish.submenu_id)
            menu_id = submenu_id_to_menu_id[submenu_id]
            await self.post(
                settings.url.target_dishes.format(
                    target_menu_id=menu_id,
                    target_submenu_id=submenu_id,
                ),
                dish.model_dump_json()
            )

    async def get_entity_ids(self, url: str) -> list[str]:
        return [entity['id'] for entity in await self.get(url)]

    async def update_entity(self,
                            schema_type: type[BaseSchema],
                            url: str,
                            id_to_entity_from_excel: dict[UUID, EntityFromExcel]) -> None:
        answer = await self.get(url)
        schema_answer = schema_type(**answer)
        entity_from_excel = id_to_entity_from_excel[schema_answer.id]
        fields = entity_from_excel.model_fields_set
        for field in fields:
            if getattr(entity_from_excel, field) != getattr(schema_answer, field):
                await self.put(url, entity_from_excel.model_dump_json())
                break

    async def update_entities(self,
                              ids_from_db: set[str],
                              schema_type: type[BaseSchema],
                              url: str,
                              id_to_entity_from_excel: dict[UUID, EntityFromExcel]) -> None:

        for entity_id in ids_from_db:
            try:
                await self.update_entity(schema_type, url.format(entity_id), id_to_entity_from_excel)
            except ValueError:
                await self.post(url, id_to_entity_from_excel)

    async def delete_difference_ids(self, difference_ids: set[str], url: str) -> None:
        for id_ in difference_ids:
            await self.delete(url.format(id_))

    async def post_difference_ids(self,
                                  difference_ids: set[str],
                                  url: str,
                                  id_to_entity_from_excel: dict[UUID, EntityFromExcel]) -> None:
        for id_ in difference_ids:
            await self.post(url, id_to_entity_from_excel[UUID(id_)].model_dump_json())




    @staticmethod
    async def _generate_hash(file: IO) -> str:
        hash_ = hashlib.sha256()
        hash_.update(file.read())
        return hash_.hexdigest()

    async def _load_file(self, path: str, mode: str = 'rb') -> IO:
        self.file = open(path, mode)
        return self.file

    async def _check_hash_file(self) -> bool:
        hash_ = await self._generate_hash(self.file)
        if self.hash_file is None or self.hash_file != hash_:
            self.hash_file = hash_
            return True
        return False




if __name__ == '__main__':
    async def main():
        parser = ParserXlsxService()
        await parser.load_sheet('../admin/Menu_2.xlsx')
        restaurant_menu = parser.get_restaurant_menu()
        client = HttpClientAdminRestaurant()
        await client.load_restaurant_menu_in_db(restaurant_menu)

    asyncio.run(main())
