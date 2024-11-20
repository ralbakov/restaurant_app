import asyncio
import io

import httpx
import openpyxl

from utils.file_service.base_file_service import BaseFileService


class ParseXlsxService(BaseFileService):
    def __init__(self, file):
        self.wb = openpyxl.load_workbook()
        super().__init__()

