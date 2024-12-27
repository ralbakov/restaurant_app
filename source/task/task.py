import asyncio
import logging

from celery import Celery

from task.parser_xlsx_service import ParserXlsxService
from task.http_client_admin_restaurant import HttpClientAdminRestaurant
from core.config import settings


celery = Celery('task_update_menu', broker=settings.celery.broker_url)
parser = ParserXlsxService()
client = HttpClientAdminRestaurant()

async def update_menu(
        parser_xlsx_service: ParserXlsxService,
        http_client_admin: HttpClientAdminRestaurant
) -> None:
    if not await parser_xlsx_service.check_hash_file(settings.file_path):
        return
    await parser_xlsx_service.load_sheet(settings.file_path)
    menu = parser_xlsx_service.get_restaurant_menu()
    await http_client_admin.load_restaurant_menu_in_db(menu)

@celery.task(
    default_retry_delay=15,
    max_retries=None,
)
def create_task_update_menu(parser, client):
    try:
        asyncio.run(update_menu(parser, client))
    except Exception as error:
        logging.error(error)
    finally:
        create_task_update_menu.retry()
