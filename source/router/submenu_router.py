from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status

from core.config import settings
from database.schemas import Submenu, SubmenuCreation, SubmenuUpdation
from service.restaurant_service import RestaurantService, TargetCode


path = settings.url

tag_submenu = 'Submenu'

RestaurantService = Annotated[RestaurantService, Depends(RestaurantService)]

submenu_router = APIRouter(prefix=path.target_submenus, tags=[tag_submenu])


@submenu_router.post('', name='Create submenu', status_code=status.HTTP_201_CREATED, response_model=Submenu)
async def create(target_menu_id: str,
                 schema: SubmenuCreation,
                 task: BackgroundTasks,
                 service: RestaurantService):
    target = TargetCode.get_target(tag_submenu)
    target.menu_id = target_menu_id
    try:
        return await service.create(schema, target, task)
    except Exception as error:
        raise HTTPException(status_code=400, detail=error.args[0])

@submenu_router.get('', name='Get all submenu', status_code=status.HTTP_200_OK, response_model=list[Submenu])
async def read_all(target_menu_id: str, task: BackgroundTasks, service: RestaurantService):
    target = TargetCode.get_target(tag_submenu)
    target.menu_id = target_menu_id
    return await service.read_all(target, task)

@submenu_router.get(path.target_submenu_id, name='Get one submenu', status_code=200, response_model=Submenu)
async def read_one(target_menu_id: str,
                   target_submenu_id: str,
                   task: BackgroundTasks,
                   service: RestaurantService):
    target = TargetCode.get_target(tag_submenu)
    target.menu_id = target_menu_id
    target.submenu_id = target_submenu_id
    try:
        return await service.read_one(target, task)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=error.args[0])

@submenu_router.patch(path.target_submenu_id,
                      name='Update submenu',
                      status_code=status.HTTP_200_OK,
                      response_model=Submenu)
async def update(target_menu_id: str,
                 target_submenu_id: str,
                 schema: SubmenuUpdation,
                 task: BackgroundTasks,
                 service: RestaurantService):
    target = TargetCode.get_target(tag_submenu)
    target.menu_id = target_menu_id
    target.submenu_id = target_submenu_id
    try:
        return await service.update(schema, target, task)
    except Exception as error:
        raise error

@submenu_router.delete(path.target_submenu_id,
                       name='Delete submenu',
                       status_code=status.HTTP_200_OK,
                       response_model=None)
async def delete(target_menu_id: str,
                 target_submenu_id: str,
                 task: BackgroundTasks,
                 service: RestaurantService):
    target = TargetCode.get_target(tag_submenu)
    target.menu_id = target_menu_id
    target.submenu_id = target_submenu_id
    try:
        return await service.delete(target, task)
    except Exception as error:
        raise HTTPException(status_code=404, detail=error.args[0])
