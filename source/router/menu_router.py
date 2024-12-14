from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from core.config import settings
from database.schemas import Menu, MenuCreation, MenuUpdation
from service.restaurant_service import RestaurantService, TargetCode, EntityName


path = settings.url

entity_name = EntityName.MENU

menu_router = APIRouter(prefix=path.target_menus, tags=['Menu'])

@menu_router.post('', name='Create menu', status_code=201, response_model=Menu)
async def create(schema: MenuCreation, task: BackgroundTasks, service: RestaurantService = Depends()):
    target = TargetCode.get_target(entity_name)
    try:
        return await service.create(schema, target, task)
    except Exception as error:
        raise HTTPException(status_code=400, detail=error.args[0])

@menu_router.get('', name='Get all menu', status_code=200, response_model=list[Menu])
async def read_all(task: BackgroundTasks, service: RestaurantService=Depends()):
    target = TargetCode.get_target(entity_name)
    return await service.read_all(target, task)


@menu_router.get(path.target_menu_id, name='Get one menu', status_code=200, response_model=Menu)
async def read_one(target_menu_id: str, task: BackgroundTasks, service: RestaurantService=Depends()):
    target = TargetCode.get_target(entity_name)
    target.menu_id = target_menu_id
    try:
        return await service.read_one(target, task)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=error.args[0])


@menu_router.patch(path.target_menu_id, name='Update menu', status_code=200, response_model=Menu)
async def update(target_menu_id: str,
                 schema: MenuUpdation,
                 task: BackgroundTasks,
                 service: RestaurantService=Depends()):
    target = TargetCode.get_target(entity_name)
    target.menu_id = target_menu_id
    try:
        return await service.update(schema, target, task)
    except Exception as error:
        raise HTTPException(status_code=400, detail=error.args[0])


@menu_router.delete(path.target_menu_id, name='Delete menu', status_code=200)
async def delete(target_menu_id: str, task: BackgroundTasks, service: RestaurantService=Depends()):
    target = TargetCode.get_target(entity_name)
    target.menu_id = target_menu_id
    try:
        return await service.delete(target, task)
    except Exception as error:
        raise HTTPException(status_code=400, detail=error.args[0])
