from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from core.config import settings
from database.session_manager import close_engine
from router.dish_router import dish_router
from router.menu_router import menu_router
from router.submenu_router import submenu_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_engine()

app = FastAPI(lifespan=lifespan,
              title='Restaurant API',
              description=('Приложение для работы с меню ресторана, '
                           'включая работу с подменю и блюдами'),
              version='3.0',
              openapi_tags=[
                  {
                      'name': 'Menu',
                      'description': 'Работа с меню',
                  },
                  {
                      'name': 'Submenu',
                      'description': 'Работа с подменю',
                  },
                  {
                      'name': 'Dish',
                      'description': 'Работа с блюдами',
                  },
              ],
              )


app.include_router(menu_router)
app.include_router(submenu_router)
app.include_router(dish_router)



if __name__ == '__main__':
    uvicorn.run('main:app', reload=True, host=settings.url.host, port=settings.url.port)
