from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status

from core.config import settings
from database.schemas import Menu, MenuCreation, MenuUpdation
from service.restaurant_service import TargetCode, RestaurantService


path = settings.url

tag_menu = 'Menu'

RestaurantService = Annotated[RestaurantService, Depends(RestaurantService)]

menu_router = APIRouter(prefix=path.target_menus, tags=[tag_menu])


@menu_router.post('', name='Create menu', status_code=status.HTTP_201_CREATED, response_model=Menu)
async def create(schema: MenuCreation, task: BackgroundTasks, service: RestaurantService):
    target = TargetCode.get_target(tag_menu)
    try:
        return await service.create(schema, target, task)
    except Exception as error:
        raise HTTPException(status_code=400, detail=error.args[0])

@menu_router.get('', name='Get all menu', status_code=status.HTTP_200_OK, response_model=list[Menu])
async def read_all(task: BackgroundTasks, service: RestaurantService):
    target = TargetCode.get_target(tag_menu)
    return await service.read_all(target, task)


@menu_router.get(path.target_menu_id, name='Get one menu', status_code=status.HTTP_200_OK, response_model=Menu)
async def read_one(target_menu_id: str, task: BackgroundTasks, service: RestaurantService):
    target = TargetCode.get_target(tag_menu)
    target.menu_id = target_menu_id
    try:
        return await service.read_one(target, task)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=error.args[0])


@menu_router.patch(path.target_menu_id, name='Update menu', status_code=status.HTTP_200_OK, response_model=Menu)
async def update(target_menu_id: str,
                 schema: MenuUpdation,
                 task: BackgroundTasks,
                 service: RestaurantService):
    target = TargetCode.get_target(tag_menu)
    target.menu_id = target_menu_id
    try:
        return await service.update(schema, target, task)
    except Exception as error:
        raise HTTPException(status_code=400, detail=error.args[0])


@menu_router.delete(path.target_menu_id, name='Delete menu', status_code=status.HTTP_200_OK)
async def delete(target_menu_id: str, task: BackgroundTasks, service: RestaurantService):
    target = TargetCode.get_target(tag_menu)
    target.menu_id = target_menu_id
    try:
        return await service.delete(target, task)
    except Exception as error:
        raise HTTPException(status_code=400, detail=error.args[0])
