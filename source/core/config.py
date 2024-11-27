import os
from dataclasses import dataclass
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
    url: str = f'postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}'
    # create_db_url: str = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}'

@dataclass
class RedisSettings:
    host: str = os.environ['REDIS_HOST']
    port: str = os.environ['REDIS_PORT']
    url: str = f'redis://{host}:{port}'
    exp_second_set: int = 600

@dataclass
class UrlPathSettings:
    prefix: str = '/api/v1'
    target_menus: str = f'{prefix}/menus'
    target_menu_id: str = '/{target_menu_id}'
    target_submenus: str = f'{target_menus}{target_menu_id}/submenus'
    target_submenu_id: str = '/{target_submenu_id}'
    target_dishes: str = f'{target_submenus}{target_submenu_id}/dishes'
    target_dish_id: str = '/{target_dish_id}'


class Settings:
    db: DbSettings = DbSettings()
    redis_cache: RedisSettings = RedisSettings()
    path: UrlPathSettings = UrlPathSettings()


settings = Settings()
