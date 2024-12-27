from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any


class AbstractHttpClient(ABC):
    @property
    @asynccontextmanager
    @abstractmethod
    async def client(self):
        pass

    @abstractmethod
    async def get(self, url: str) -> Any:
        pass

    @abstractmethod
    async def post(self, url: str, json_data: str) -> Any:
        pass

    @abstractmethod
    async def patch(self, url: str, json_data: str) -> Any:
        pass

    async def delete(self, url: str) -> Any:
        pass
