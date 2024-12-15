import logging

from celery import Celery

from task.parser_xlsx_service import ParserXlsxService
from task.http_client_admin_restaurant import HttpClientAdminRestaurant
from core.config import settings

celery = Celery('task_menu', broker=f'amqp://rb')
parser = ParserXlsxService()
client = HttpClientAdminRestaurant()

@celery.task(
    default_retry_delay=15,
    max_retries=None,
)
def update_base(parser: ParserXlsxService):

    try:
        pass
    except Exception as error:
        logging.error(error)
    finally:
        update_base.retry()