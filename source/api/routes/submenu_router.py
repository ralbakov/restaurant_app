from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from core.config import settings
from database.models import Submenu as Entity
from database.schemas import Submenu, SubmenuCreation, SubmenuUpdation
from service.restaurant_menu_service import RestaurantMenuService, TargetCode


path = settings.path

submenu_router = APIRouter(prefix=path.target_submenus, tags=['Submenu'])


@submenu_router.post('', name='Create submenu', status_code=201, response_model=Submenu)
async def create(target_menu_id: str, creation_schema: SubmenuCreation, task: BackgroundTasks, service: RestaurantMenuService = Depends()):
    target_code = TargetCode.construct_entity_name(Entity)
    target_code.menu = target_menu_id
    try:
        return await service.create(creation_schema, target_code, task)
    except Exception as error:
        raise HTTPException(status_code=400, detail=error.args[0])


@submenu_router.get('', name='Get all submenu', status_code=200, response_model=list[Submenu])
async def read_all(target_menu_id: str, task: BackgroundTasks, service: RestaurantMenuService = Depends()):
    target_code = TargetCode.construct_entity_name(Entity)
    target_code.menu = target_menu_id
    return await service.read_all(target_code, task)


@submenu_router.get(path.target_submenu_id, name='Get one submenu', status_code=200, response_model=Submenu)
async def read_one(target_menu_id: str,
                   target_submenu_id: str,
                   task: BackgroundTasks,
                   service: RestaurantMenuService = Depends()):
    target_code = TargetCode.construct_entity_name(Entity)
    target_code.menu = target_menu_id
    target_code.submenu = target_submenu_id
    try:
        return await service.read_one(target_code, task)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=error.args[0])


@submenu_router.patch(path.target_submenu_id, name='Update submenu', status_code=200, response_model=Submenu)
async def update(target_menu_id: str,
                 target_submenu_id: str,
                 updation_schema: SubmenuUpdation,
                 task: BackgroundTasks,
                 service: RestaurantMenuService = Depends()):
    target_code = TargetCode.construct_entity_name(Entity)
    target_code.menu = target_menu_id
    target_code.submenu = target_submenu_id
    try:
        return await service.update(updation_schema, target_code, task)
    except Exception as error:
        raise error


@submenu_router.delete(path.target_submenu_id, name='Delete submenu', status_code=200, response_model=None)
async def delete(target_menu_id: str,
                 target_submenu_id: str,
                 task: BackgroundTasks,
                 service: RestaurantMenuService = Depends()):
    target_code = TargetCode.construct_entity_name(Entity)
    target_code.menu = target_menu_id
    target_code.submenu = target_submenu_id
    try:
        return await service.delete(target_code, task)
    except Exception as error:
        raise HTTPException(status_code=404, detail=error.args[0])
