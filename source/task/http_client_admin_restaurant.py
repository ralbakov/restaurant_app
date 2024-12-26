import asyncio
import hashlib
import json
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any, IO, TypeVar

import httpx

from abstract_http_client import AbstractHttpClient
from core.config import settings
from database.schemas import Menu, Submenu, Dish
from parser_xlsx_service import RestaurantMenu, ParserXlsxService


EntityFromExcel = TypeVar("EntityFromExcel", Menu, Submenu, Dish)


class HttpClientAdminRestaurant(AbstractHttpClient):
    def __init__(self):
        self.base_url: str = f'http://{settings.url.host}:{settings.url.port}'
        self.hash_file: str | None = None
        self.file: IO | None = None

    @property
    @asynccontextmanager
    async def get_client(self):
        client = httpx.AsyncClient(base_url=self.base_url)
        try:
            yield client
        finally:
            await client.aclose()

    async def get(self, url: str) -> Any:
        async with self.get_client as client:
            response = await client.get(url)
            if response.status_code != 200:
                raise ValueError
            return response.json()

    async def post(self, url: str, json_data: str) -> None:
        async with self.get_client as client:
            await client.post(url, data=json_data)

    async def patch(self, url: str, json_data: str) -> None:
        async with self.get_client as client:
            await client.patch(url, data=json_data)

    async def delete(self, url: str) -> None:
        async with self.get_client as client:
            await client.delete(url)

    async def load_restaurant_menu_in_db(self, restaurant_menu: RestaurantMenu) -> None:
        menu_ids_from_db = set(await self.get_entity_ids(settings.url.target_menus))
        if not menu_ids_from_db:
            return await self.post_entity(restaurant_menu)

        target_menus = settings.url.target_menus
        target_menu_id = settings.url.target_menu_id
        target_submenus = settings.url.target_submenus
        target_submenu_id = settings.url.target_submenu_id
        target_dishes = settings.url.target_dishes
        target_dish_id = settings.url.target_dish_id

        menu_ids_from_excel = set(restaurant_menu.menu_id_to_menu)
        diff = menu_ids_from_db - menu_ids_from_excel
        if diff:
            menu_id_url = target_menus + target_menu_id
            for difference in diff:
                await self.delete(menu_id_url.format(target_menu_id=difference))

        menu_id_to_submenu_ids_from_db, menu_id_to_submenu_ids_from_excel = {}, {}
        for menu_id in menu_ids_from_excel:
            menu = restaurant_menu.menu_id_to_menu[menu_id]
            menu_id_url = target_menus + target_menu_id.format(target_menu_id=menu_id)
            await self.update_or_post_entity(target_menus, menu_id_url, menu)
            menu_id_to_submenu_ids_from_db[menu_id] = set(
                await self.get_entity_ids(target_submenus.format(target_menu_id=menu_id))
            )
            menu_id_to_submenu_ids_from_excel[menu_id] = set()

        menu_id_submenu_id_to_dish_ids_from_db, menu_id_submenu_id_to_dish_ids_from_excel = {}, {}
        for (menu_id, submenu_id), submenu in restaurant_menu.menu_id_submenu_id_to_submenu.items():
            menu_id_to_submenu_ids_from_excel[menu_id].add(submenu_id)
            submenus_url = target_submenus.format(target_menu_id=menu_id)
            submenu_id_url = submenus_url + target_submenu_id.format(target_submenu_id=submenu_id)
            await self.update_or_post_entity(submenus_url, submenu_id_url, submenu)
            menu_id_submenu_id_to_dish_ids_from_db[(menu_id, submenu_id)] = set(
                await self.get_entity_ids(target_dishes.format(target_menu_id=menu_id, target_submenu_id=submenu_id))
            )
            menu_id_submenu_id_to_dish_ids_from_excel[(menu_id, submenu_id)] = set()

        for id_ in menu_id_to_submenu_ids_from_db:
            diff = menu_id_to_submenu_ids_from_db[id_] - menu_id_to_submenu_ids_from_excel[id_]
            if diff:
                submenu_id_url = target_submenus + target_submenu_id
                for difference in diff:
                    await self.delete(submenu_id_url.format(target_menu_id=id_, target_submenu_id=difference))

        for (menu_id, submenu_id, dish_id), dish in restaurant_menu.menu_id_submenu_id_dish_id_to_dish.items():
            dishes_url = target_dishes.format(target_menu_id=menu_id, target_submenu_id=submenu_id)
            dish_id_url = dishes_url + target_dish_id.format(target_dish_id=dish_id)
            await self.update_or_post_entity(dishes_url, dish_id_url, dish)
            menu_id_submenu_id_to_dish_ids_from_excel[(menu_id, submenu_id)].add(dish_id)

        for id_ in menu_id_submenu_id_to_dish_ids_from_db:
            diff = menu_id_submenu_id_to_dish_ids_from_db[id_] - menu_id_submenu_id_to_dish_ids_from_excel[id_]
            if diff:
                menu_id, submenu_id = id_
                dish_id_url = target_dishes + target_dish_id
                for difference in diff:
                    await self.delete(
                        dish_id_url.format(
                            target_menu_id=menu_id,
                            target_submenu_id=submenu_id,
                            target_dish_id=difference
                        )
                    )

    async def post_entity(self, restaurant_menu: RestaurantMenu) -> None:
        for menu in restaurant_menu.menu_id_to_menu.values():
            await self.post(settings.url.target_menus, menu.model_dump_json())

        for (menu_id, _), submenu in restaurant_menu.menu_id_submenu_id_to_submenu.items():
            await self.post(settings.url.target_submenus.format(target_menu_id=menu_id), submenu.model_dump_json())

        for (menu_id, submenu_id, _), dish in restaurant_menu.menu_id_submenu_id_dish_id_to_dish.items():
            await self.post(
                settings.url.target_dishes.format(target_menu_id=menu_id, target_submenu_id=submenu_id),
                dish.model_dump_json(),
            )

    async def get_entity_ids(self, url: str) -> list[str]:
        return [entity['id'] for entity in await self.get(url)]

    async def update_or_post_entity(self, post_url: str, target_url: str, entity_from_excel: EntityFromExcel) -> None:
        model_dump_json = entity_from_excel.model_dump_json()
        column_to_value = json.loads(model_dump_json)
        try:
            answer = await self.get(target_url)
        except ValueError:
            return await self.post(post_url, model_dump_json)

        columns = column_to_value.keys()
        if (discount := column_to_value.get('discount')) is not None:
            column_to_value['price'] = str(
                (entity_from_excel.price * Decimal(1 - discount / 100)).quantize(Decimal('1.00'))
            )

        for column in columns:
            if column_to_value[column] != answer[column] and column_to_value[column] is not None:
                await self.patch(target_url, model_dump_json)
                break

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
        await parser.load_sheet(settings.file_path)
        restaurant_menu = parser.get_restaurant_menu()
        client = HttpClientAdminRestaurant()
        await client.load_restaurant_menu_in_db(restaurant_menu)

    asyncio.run(main())
