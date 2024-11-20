from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from typing_extensions import TypeVar


URL = TypeVar('URL')

class AbstractFileService(ABC):
    @abstractmethod
    @asynccontextmanager
    async def get_file(self, url: URL) -> AsyncGenerator:
        try:
            yield
        finally:
            pass

    @abstractmethod
    async def open_file(self, file_path: str, mode: str) -> bytes:
        pass

    @abstractmethod
    async def construct_hash(self, file_path: URL | str, mode: str = 'rb') -> str:
        pass
