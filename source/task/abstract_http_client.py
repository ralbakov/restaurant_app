from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any


class AbstractHttpClient(ABC):
    @property
    @asynccontextmanager
    @abstractmethod
    async def get_client(self):
        pass

    @abstractmethod
    async def get(self, url: str) -> Any:
        pass

    @abstractmethod
    async def post(self, url: str, data: dict[str, Any]) -> Any:
        pass

    @abstractmethod
    async def put(self, url: str, data: dict[str, Any]) -> Any:
        pass
