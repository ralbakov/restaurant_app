import asyncio

from celery import Celery

from task.parser_xlsx_service import ParserXlsxService
from task.http_client_admin_restaurant import HttpClientAdminRestaurant
from core.config import settings


celery = Celery('update_menu', broker=settings.celery.broker_url)
parser = ParserXlsxService()
client = HttpClientAdminRestaurant()


async def update_menu() -> None:
    if not await parser.check_hash_file(settings.file_path):
        return
    await parser.load_sheet(settings.file_path)
    menu = parser.get_restaurant_menu()
    return await client.load_restaurant_menu_in_db(menu)


@celery.task(
    default_retry_delay=15,
    max_retries=None,
)
def create_task_update_menu():
    try:
        asyncio.run(update_menu())
    except Exception as error:
        print(repr(error))
    finally:
        create_task_update_menu.retry()
