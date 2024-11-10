from fastapi import APIRouter, Depends, HTTPException

from database.models import Submenu as Entity
from database.schemas import Submenu, SubmenuCreation, SubmenuUpdation
from service.restaurant_menu_service import RestaurantMenuService, RedisCacheName

submenu_router = APIRouter(prefix='/api/v1/menus/{target_menu_id}/submenus', tags=['Submenu'])


def get_entity_name() -> str:
    return Entity.__name__.lower()


@submenu_router.post('', name='Create submenu', status_code=201, response_model=Submenu)
async def create(target_menu_id: str, creation_schema: SubmenuCreation, service: RestaurantMenuService=Depends()):
    identification = RedisCacheName(menu_id=target_menu_id)
    try:
        return await service.create(get_entity_name(), creation_schema, identification)
    except Exception as error:
        raise HTTPException(status_code=400, detail=error.args[0])


@submenu_router.get('', name='Get all submenu', status_code=200, response_model=list[Submenu])
async def read_all(target_menu_id: str, service: RestaurantMenuService=Depends()):
    identification = RedisCacheName(menu_id=target_menu_id)
    return await service.read_all(get_entity_name(), identification)


@submenu_router.get('/{target_submenu_id}', name='Get one submenu', status_code=200, response_model=Submenu)
async def read_one(target_menu_id: str, target_submenu_id: str, service: RestaurantMenuService=Depends()):
    identification = RedisCacheName(menu_id=target_menu_id, submenu_id=target_submenu_id)
    try:
        return await service.read_one(get_entity_name(), target_submenu_id, identification)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=error.args[0])


@submenu_router.patch('/{target_submenu_id}', name='Update submenu', status_code=200, response_model=Submenu)
async def update(
        target_menu_id: str,
        target_submenu_id: str,
        updation_schema: SubmenuUpdation,
        service: RestaurantMenuService=Depends(),
):
    identification = RedisCacheName(menu_id=target_menu_id, submenu_id=target_submenu_id)
    try:
        return await service.update(get_entity_name(), target_submenu_id, updation_schema, identification)
    except Exception as error:
        raise error


@submenu_router.delete('/{target_submenu_id}', name='Delete submenu', status_code=200, response_model=None)
async def delete(target_menu_id: str, target_submenu_id: str, service: RestaurantMenuService=Depends()):
    identification = RedisCacheName(menu_id=target_menu_id, submenu_id=target_submenu_id)
    try:
        return await service.delete(get_entity_name(), target_submenu_id, identification)
    except Exception as error:
        raise HTTPException(status_code=404, detail=error.args[0])
