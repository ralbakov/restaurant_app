import asyncio
import hashlib
from contextlib import asynccontextmanager

import httpx

from utils.file_service.abstract_file_service import AbstractFileService


class BaseFileService(AbstractFileService):
    def __init__(self):
        self.hash_: str = ''
        self.file: bytes = b''

    @asynccontextmanager
    async def get_file(self, url: httpx.URL):
        client = httpx.AsyncClient()
        response = await client.get(url)
        print(response.content)
        if not response or response.status_code != 200:
            raise ValueError(f"Failed to download file from {url}")
        try:
            yield response
        finally:
            await client.aclose()

    async def open_file(self, file_path: str, mode: str) -> bytes:
        with open(file_path, mode) as file:
            return file

    async def construct_hash(self, file_path: httpx.URL | str, mode: str = 'rb') -> str:
        hash_ = hashlib.sha256()
        if isinstance(file_path, httpx.URL):
            async with self.get_file(file_path) as response:
                data = response.read()
        else:
            data = await self.open_file(file_path, mode)
        hash_.update(data)
        self.hash_ = hash_.hexdigest()
        self.file = data
        return self.hash_

if __name__ == '__main__':
    file_ser = BaseFileService()
    async def main():
        sha256_hash = await file_ser.construct_hash(httpx.URL("https://docs.google.com/spreadsheets/d/1MwsuSEoy0BkhXLpuM04xmTGTxvuEEyOBtXA0DfXID1s/edit?usp=share_link"))
        print(sha256_hash)

    asyncio.run(main())
