from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any

import httpx

from core.config import settings
from task.abstract_http_client import AbstractHttpClient
from task.parser_xlsx_service import RestaurantMenu


class HttpClientAdminRestaurant(AbstractHttpClient):
    def __init__(self):
        self.host = settings.url.host
        self.port = settings.url.port
        self.client = httpx.AsyncClient(base_url=f'http://{self.host}:{self.port}')

    @property
    @asynccontextmanager
    async def get_client(self) -> AsyncGenerator[httpx.AsyncClient]:
        client = self.client
        try:
            yield client
        finally:
            await client.aclose()

    async def get(self, url: str) -> Any:
        async with self.get_client as client:
            return await client.get(url).json()

    async def post(self, url: str, data: dict[str, Any]) -> Any:
        async with self.get_client as client:
            return await client.post(url, data=data)

    async def put(self, url: str, data: dict[str, Any]) -> Any:
        async with self.get_client as client:
            return await client.put(url, data=data)

    async def load_restaurant_menu_in_db(self, restaurant_menu: RestaurantMenu):
        pass