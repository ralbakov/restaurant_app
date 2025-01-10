import asyncio
from datetime import timedelta

from celery import Celery

from core.config import settings
from task.http_client_admin_restaurant import HttpClientAdminRestaurant
from task.parser_xlsx_service import ParserXlsxService


celery = Celery(broker=settings.celery.broker_url)

celery.conf.beat_schedule = {
    'load_menu': {
        'task': 'load_menu',
        'schedule': timedelta(seconds=15),
    },
}

parser = ParserXlsxService()

client = HttpClientAdminRestaurant()

async def _load_menu() -> str:
    if not await parser.check_hash_file(settings.file_path):
        return 'Menu has not been changed'
    parser.load_sheet(settings.file_path)
    menu = await parser.get_restaurant_menu()
    await client.load_restaurant_menu_in_db(menu)
    return 'Menu update successfully'


@celery.task(
    name='load_menu',
    bind=True,
    default_retry_delay=15,
    max_retries=None,
)
def load_menu(self):
    try:
        return asyncio.run(_load_menu())
    except Exception as error:
        self.retry(exc=error)
