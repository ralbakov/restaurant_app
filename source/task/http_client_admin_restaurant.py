import asyncio
import hashlib
from contextlib import asynccontextmanager
from typing import Any

import httpx

from core.config import settings
from task.abstract_http_client import AbstractHttpClient
from task.parser_xlsx_service import RestaurantMenu, ParserXlsxService


class HttpClientAdminRestaurant(AbstractHttpClient):
    def __init__(self):
        self.base_url: str = f'http://{settings.url.host}:{settings.url.host}'
        self.hash_file: str | None = None

    @property
    @asynccontextmanager
    async def get_client(self):
        client = httpx.AsyncClient(base_url=self.base_url)
        try:
            yield client
        finally:
            await client.aclose()

    async def get(self, url: str) -> dict[str, Any]:
        async with self.get_client as client:
            return (await client.get(url)).json()

    async def post(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
        async with self.get_client as client:
            return (await client.post(url, json=data)).json()

    async def put(self, url: str, data: dict[str, Any]) -> dict[str, Any]:
        async with self.get_client as client:
            return (await client.put(url, json=data)).json()

    async def load_restaurant_menu_in_db(self, restaurant_menu: RestaurantMenu):
        menu_titles = await self.get_titles(settings.url.target_menus)
        if not menu_titles:
            await self.post_entity(restaurant_menu)
        pass

    async def post_entity(self, restaurant_menu: RestaurantMenu) -> None:
        for menu in restaurant_menu.menus:
            await self.post(settings.url.target_menus, menu.as_dict())
        submenu_id_to_menu_id = {}
        for submenu in restaurant_menu.submenus:
            menu_id = submenu.menu_id
            await self.post(
                settings.url.target_submenus.format(target_menu_id=menu_id),
                submenu.as_dict(),
            )
            submenu_id_to_menu_id[submenu.id] = menu_id
        for dish in restaurant_menu.dishes:
            submenu_id = dish.submenu_id
            menu_id = submenu_id_to_menu_id[submenu_id]
            await self.post(
                settings.url.target_dishes.format(
                    target_menu_id=menu_id,
                    target_submenu_id=submenu_id,
                ),
                dish.as_dict()
            )

    async def get_titles(self, url: str) -> list[str]:
        return [value['title'] for value in await self.get(url)]

    @staticmethod
    async def __generate_hash(path: str) -> str:
        hash_ = hashlib.sha256()
        with open(path, 'rb') as file:
            hash_.update(file.read())
        return hash_.hexdigest()

    async def check_hash_file(self, path: str) -> bool:
        hash_ = await self.__generate_hash(path)
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
