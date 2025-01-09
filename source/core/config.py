import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


BASE_DIR = Path(__file__).absolute().parent.parent.parent


@dataclass
class DbSettings:
    POSTGRES_PASSWORD: str = os.environ['POSTGRES_PASSWORD']
    POSTGRES_USER: str = os.environ['POSTGRES_USER']
    POSTGRES_DB: str = os.environ['POSTGRES_DB']
    POSTGRES_HOST: str = os.environ['POSTGRES_HOST']
    POSTGRES_PORT: str = os.environ['POSTGRES_PORT']
    url: str = f'postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}'

@dataclass
class RedisSettings:
    REDIS_HOST: str = os.environ['REDIS_HOST']
    REDIS_PORT: str = os.environ['REDIS_PORT']
    url: str = f'redis://{REDIS_HOST}:{REDIS_PORT}'
    ttl: int = timedelta(minutes=15).seconds

@dataclass
class UrlSettings:
    host: str = 'backend'
    port: int = 8080
    prefix: str = '/api/v1'
    target_menus: str = f'{prefix}/menus'
    target_menu_id: str = '/{target_menu_id}'
    target_submenus: str = f'{target_menus}{target_menu_id}/submenus'
    target_submenu_id: str = '/{target_submenu_id}'
    target_dishes: str = f'{target_submenus}{target_submenu_id}/dishes'
    target_dish_id: str = '/{target_dish_id}'

class CelerySettings:
    RABBITMQ_DEFAULT_USER: str = os.environ['RABBITMQ_DEFAULT_USER']
    RABBITMQ_DEFAULT_PASS: str = os.environ['RABBITMQ_DEFAULT_PASS']
    RABBITMQ_DEFAULT_PORT: int = os.environ['RABBITMQ_DEFAULT_PORT']
    RABBITMQ_HOST: str = os.environ['RABBITMQ_HOST']
    RABBITMQ_DEFAULT_VHOST: str = os.environ['RABBITMQ_DEFAULT_VHOST']
    broker_url = f'amqp://{RABBITMQ_DEFAULT_USER}:{RABBITMQ_DEFAULT_PASS}@{RABBITMQ_HOST}:{RABBITMQ_DEFAULT_PORT}/{RABBITMQ_DEFAULT_VHOST}'

class Settings:
    db: DbSettings = DbSettings()
    redis_cache: RedisSettings = RedisSettings()
    url: UrlSettings = UrlSettings()
    celery: CelerySettings = CelerySettings()
    file_path: str = BASE_DIR / 'source/admin/Menu_2.xlsx'

settings = Settings()
