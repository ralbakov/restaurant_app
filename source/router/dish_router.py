from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from starlette import status

from core.config import settings
from database.schemas import Dish, DishCreation, DishUpdation
from service.restaurant_service import RestaurantService, TargetCode


path = settings.url

tag_dish = 'Dish'

RestaurantService = Annotated[RestaurantService, Depends(RestaurantService)]

dish_router = APIRouter(prefix=path.target_dishes, tags=[tag_dish])


@dish_router.post('', name='Create dish', status_code=status.HTTP_201_CREATED, response_model=Dish)
async def create(target_menu_id: str,
                 target_submenu_id: str,
                 schema: DishCreation,
                 task: BackgroundTasks,
                 service: RestaurantService):
    target = TargetCode.get_target(tag_dish)
    target.menu_id = target_menu_id
    target.submenu_id = target_submenu_id
    try:
        return await service.create(schema, target, task)
    except Exception as error:
        raise HTTPException(status_code=400, detail=error.args[0])


@dish_router.get('', name='Get all dish', status_code=status.HTTP_200_OK, response_model=list[Dish])
async def read_all(target_menu_id: str,
                   target_submenu_id: str,
                   task: BackgroundTasks,
                   service: RestaurantService):
    target = TargetCode.get_target(tag_dish)
    target.menu_id = target_menu_id
    target.submenu_id = target_submenu_id
    return await service.read_all(target, task)


@dish_router.get(path.target_dish_id, name='Get one dish', status_code=status.HTTP_200_OK, response_model=Dish)
async def read_one(target_menu_id: str,
                   target_submenu_id: str,
                   target_dish_id: str,
                   task: BackgroundTasks,
                   service: RestaurantService):
    target = TargetCode.get_target(tag_dish)
    target.menu_id = target_menu_id
    target.submenu_id = target_submenu_id
    target.dish_id = target_dish_id
    try:
        return await service.read_one(target, task)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=error.args[0])


@dish_router.patch(path.target_dish_id, name='Update dish', status_code=status.HTTP_200_OK, response_model=Dish)
async def update(target_menu_id: str,
                 target_submenu_id: str,
                 target_dish_id: str,
                 schema: DishUpdation,
                 task: BackgroundTasks,
                 service: RestaurantService):
    target = TargetCode.get_target(tag_dish)
    target.menu_id = target_menu_id
    target.submenu_id = target_submenu_id
    target.dish_id = target_dish_id
    try:
        return await service.update(schema, target, task)
    except Exception as error:
        raise error


@dish_router.delete(path.target_dish_id, name='Delete dish', status_code=status.HTTP_200_OK, response_model=None)
async def delete(target_menu_id: str,
                 target_submenu_id: str,
                 target_dish_id: str,
                 task: BackgroundTasks,
                 service: RestaurantService):
    target = TargetCode.get_target(tag_dish)
    target.menu_id = target_menu_id
    target.submenu_id = target_submenu_id
    target.dish_id = target_dish_id
    try:
        return await service.delete(target, task)
    except Exception as error:
        raise HTTPException(status_code=404, detail=error.args[0])
