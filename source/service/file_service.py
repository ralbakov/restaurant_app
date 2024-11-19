import hashlib
import io
from contextlib import asynccontextmanager

import httpx


class FileService:
    def __init__(self):
        self.sha256_hash = None
        self.file: bytes | None = None

    @asynccontextmanager
    async def get_file(self, url: httpx.URL):
        client = httpx.AsyncClient()
        response = await client.get(url)
        if not response or response.status_code != 200:
            raise ValueError(f"Failed to download file from {url}")
        try:
            yield response
        finally:
            await client.aclose()

    async def construct_sha256_hash(self, file_path: httpx.URL | str) -> str:
        sha256_hash = hashlib.sha256()
        if isinstance(file_path, httpx.URL):
            async with self.get_file(file_path) as response:
                sha256_hash.update(response.read())
        else:
            with open(file_path, 'rb') as file:
                while data := file.read(io.DEFAULT_BUFFER_SIZE):
                    sha256_hash.update(data)
        self.sha256_hash = sha256_hash.hexdigest()
        return self.sha256_hash
