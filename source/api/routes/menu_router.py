from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from core.config import settings
from database.schemas import Menu, MenuCreation, MenuUpdation
from service.restaurant_service import RestaurantService, TargetCode


path = settings.path

menu_router = APIRouter(prefix=path.target_menus, tags=['Menu'])


@menu_router.post('', name='Create menu', status_code=201, response_model=Menu)
async def create(creation_schema: MenuCreation, task: BackgroundTasks, service: RestaurantService = Depends()):
    target_code = TargetCode.construct_entity_name(Menu)
    try:
        return await service.create(creation_schema, target_code, task)
    except Exception as error:
        raise HTTPException(status_code=400, detail=error.args[0])

@menu_router.get('', name='Get all menu', status_code=200, response_model=list[Menu])
async def read_all(task: BackgroundTasks, service: RestaurantService=Depends()):
    target_code = TargetCode.construct_entity_name(Menu)
    return await service.read_all(target_code, task)


@menu_router.get(path.target_menu_id, name='Get one menu', status_code=200, response_model=Menu)
async def read_one(target_menu_id: str, task: BackgroundTasks, service: RestaurantService=Depends()):
    target_code = TargetCode.construct_entity_name(Menu)
    target_code.menu = target_menu_id
    try:
        return await service.read_one(target_code, task)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=error.args[0])


@menu_router.patch(path.target_menu_id, name='Update menu', status_code=200, response_model=Menu)
async def update(target_menu_id: str,
                 updation_schema: MenuUpdation,
                 task: BackgroundTasks,
                 service: RestaurantService=Depends()):
    target_code = TargetCode.construct_entity_name(Menu)
    target_code.menu = target_menu_id
    try:
        return await service.update(updation_schema, target_code, task)
    except Exception as error:
        raise HTTPException(status_code=400, detail=error.args[0])


@menu_router.delete(path.target_menu_id, name='Delete menu', status_code=200)
async def delete(target_menu_id: str, task: BackgroundTasks, service: RestaurantService=Depends()):
    target_code = TargetCode.construct_entity_name(Menu)
    target_code.menu = target_menu_id
    try:
        return await service.delete(target_code, task)
    except Exception as error:
        raise HTTPException(status_code=400, detail=error.args[0])
