import json
from collections import defaultdict
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any, TypeVar

from httpx import AsyncClient

from core.config import settings
from database.schemas import MenuCreation, SubmenuCreation, DishCreation
from task.abstract_http_client import AbstractHttpClient
from task.parser_xlsx_service import RestaurantMenu


EntityFromExcel = TypeVar("EntityFromExcel", MenuCreation, SubmenuCreation, DishCreation)


class HttpClientAdminRestaurant(AbstractHttpClient):
    def __init__(self):
        self.base_url: str = f'http://{settings.url.host}:{settings.url.port}'

    @property
    @asynccontextmanager
    async def client(self):
        client = AsyncClient(base_url=self.base_url)
        try:
            yield client
        finally:
            await client.aclose()

    async def get(self, url: str) -> Any:
        async with self.client as client:
            response = await client.get(url)
            if response.status_code != 200:
                return None
        return response.json()

    async def post(self, url: str, json_data: str) -> None:
        async with self.client as client:
            await client.post(url, data=json_data)

    async def patch(self, url: str, json_data: str) -> None:
        async with self.client as client:
            await client.patch(url, data=json_data)

    async def delete(self, url: str) -> None:
        async with self.client as client:
            await client.delete(url)

    async def load_restaurant_menu_in_db(self, restaurant_menu: RestaurantMenu) -> None:
        menu_ids_from_db = set(await self.get_entity_ids(settings.url.target_menus))
        if not menu_ids_from_db:
            return await self.post_entity(restaurant_menu)

        menu_ids_from_excel = set(restaurant_menu.menu_id_to_menu)
        diffs = menu_ids_from_db - menu_ids_from_excel
        if diffs:
            for diff in diffs:
                await self.delete(settings.url.target_menus + settings.url.target_menu_id.format(target_menu_id=diff))

        await self._delete_diff(restaurant_menu)
        await self.update_entity(restaurant_menu)

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

    async def update_entity(self, restaurant_menu: RestaurantMenu) -> None:
        target_menus, target_menu_id = settings.url.target_menus, settings.url.target_menu_id
        target_submenus, target_submenu_id = settings.url.target_submenus, settings.url.target_submenu_id
        target_dishes, target_dish_id = settings.url.target_dishes, settings.url.target_dish_id
        for menu_id, menu in restaurant_menu.menu_id_to_menu.items():
            menu_id_url = target_menus + target_menu_id.format(target_menu_id=menu_id)
            await self.update_or_post_entity(target_menus, menu_id_url, menu)

        for (menu_id, submenu_id), submenu in restaurant_menu.menu_id_submenu_id_to_submenu.items():
            submenus_url = target_submenus.format(target_menu_id=menu_id)
            submenu_id_url = submenus_url + target_submenu_id.format(target_submenu_id=submenu_id)
            await self.update_or_post_entity(submenus_url, submenu_id_url, submenu)

        for (menu_id, submenu_id, dish_id), dish in restaurant_menu.menu_id_submenu_id_dish_id_to_dish.items():
            dishes_url = target_dishes.format(target_menu_id=menu_id, target_submenu_id=submenu_id)
            dish_id_url = dishes_url + target_dish_id.format(target_dish_id=dish_id)
            await self.update_or_post_entity(dishes_url, dish_id_url, dish)

    async def get_entity_ids(self, url: str) -> list[str]:
        return [entity['id'] for entity in await self.get(url)]

    async def update_or_post_entity(self, post_url: str, target_url: str, entity_from_excel: EntityFromExcel) -> None:
        model_dump_json = entity_from_excel.model_dump_json()
        column_to_value = json.loads(model_dump_json)
        answer = await self.get(target_url)
        if answer is None:
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

    async def _delete_diff(self, restaurant_menu: RestaurantMenu) -> None:
        menu_id_to_submenu_ids_db, menu_id_to_submenu_ids_excel = defaultdict(set), defaultdict(set)
        menu_id_submenu_id_to_dish_ids_db, menu_id_submenu_id_to_dish_ids_excel = defaultdict(set), defaultdict(set)

        for menu_id in restaurant_menu.menu_id_to_menu.keys():
            menu_id_to_submenu_ids_db[menu_id].update(
                await self.get_entity_ids(settings.url.target_submenus.format(target_menu_id=menu_id))
            )

        for menu_id, submenu_id in restaurant_menu.menu_id_submenu_id_to_submenu.keys():
            menu_id_submenu_id_to_dish_ids_db[(menu_id, submenu_id)].update(
                await self.get_entity_ids(
                    settings.url.target_dishes.format(target_menu_id=menu_id, target_submenu_id=submenu_id)
                )
            )

        for menu_id, submenu_id, dish_id in restaurant_menu.menu_id_submenu_id_dish_id_to_dish.keys():
            menu_id_to_submenu_ids_excel[menu_id].add(submenu_id)
            menu_id_submenu_id_to_dish_ids_excel[(menu_id, submenu_id)].add(dish_id)

        for menu_id in menu_id_to_submenu_ids_excel:
            submenu_difference_ids = menu_id_to_submenu_ids_db[menu_id] - menu_id_to_submenu_ids_excel[menu_id]
            if submenu_difference_ids:
                for submenu_id in submenu_difference_ids:
                    url = settings.url.target_submenus + settings.url.target_submenu_id
                    await self.delete(url.format(target_menu_id=menu_id, target_submenu_id=submenu_id))

        for menu_id_submenu_id in menu_id_submenu_id_to_dish_ids_excel:
            dish_difference_ids = (
                    menu_id_submenu_id_to_dish_ids_db[menu_id_submenu_id]
                    - menu_id_submenu_id_to_dish_ids_excel[menu_id_submenu_id]
            )
            if dish_difference_ids:
                for dish_id in dish_difference_ids:
                    url = settings.url.target_dishes + settings.url.target_dish_id
                    await self.delete(url.format(
                        target_menu_id=menu_id_submenu_id[0],
                        target_submenu_id=menu_id_submenu_id[1],
                        target_dish_id=dish_id,
                    ))
