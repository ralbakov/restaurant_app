import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_settings import BaseSettings

load_dotenv()


BASE_DIR = Path(__file__).absolute().parent.parent.parent


class DbSettings(BaseModel):
    POSTGRES_PASSWORD: str = os.environ['POSTGRES_PASSWORD']
    POSTGRES_USER: str = os.environ['POSTGRES_USER']
    POSTGRES_DB: str = os.environ['POSTGRES_DB']
    POSTGRES_HOST: str = os.environ['POSTGRES_HOST']
    url: str = f'postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}'
    # create_db_url: str = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}'


class RedisSettings(BaseModel):
    host: str = os.environ['REDIS_HOST']
    port: str = os.environ['REDIS_PORT']
    url: str = f'redis://{host}:{port}'
    exp_second_set: int = 600


class Settings(BaseSettings):
    db: DbSettings = DbSettings()
    redis_cache: RedisSettings = RedisSettings()


settings = Settings()
