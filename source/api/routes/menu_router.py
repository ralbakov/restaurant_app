from fastapi import APIRouter, Depends, HTTPException

from database.models import Menu as Entity
from database.schemas import Menu, MenuCreation, MenuUpdation
from service.restaurant_menu_service import RestaurantMenuService, RedisCacheName

menu_router = APIRouter(prefix='/api/v1/menus', tags=['Menu'])


def get_entity_name() -> str:
    return Entity.__name__.lower()


@menu_router.post('', name='Create menu', status_code=201, response_model=Menu)
async def create(creation_schema: MenuCreation, service: RestaurantMenuService = Depends()):
    try:
        return await service.create(get_entity_name(), creation_schema)
    except Exception as error:
        raise HTTPException(status_code=400, detail=error.args[0])

@menu_router.get('', name='Get all menu', status_code=200, response_model=list[Menu])
async def read_all(service: RestaurantMenuService=Depends()):
    return await service.read_all(get_entity_name(), RedisCacheName())


@menu_router.get('/{target_menu_id}', name='Get one menu', status_code=200, response_model=Menu)
async def read_one(target_menu_id: str, service: RestaurantMenuService=Depends()):
    cache_name = RedisCacheName(menu_id=target_menu_id)
    try:
        return await service.read_one(get_entity_name(), target_menu_id, cache_name)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=error.args[0])


@menu_router.patch('/{target_menu_id}', name='Update menu', status_code=200, response_model=Menu)
async def update(target_menu_id: str, updation_schema: MenuUpdation, service: RestaurantMenuService=Depends()):
    cache_name = RedisCacheName(menu_id=target_menu_id)
    try:
        return await service.update(get_entity_name(), target_menu_id, updation_schema, cache_name)
    except Exception as error:
        raise HTTPException(status_code=400, detail=error.args[0])


@menu_router.delete('/{target_menu_id}', name='Delete menu', status_code=200)
async def delete(target_menu_id: str, service: RestaurantMenuService=Depends()):
    cache_name = RedisCacheName(menu_id=target_menu_id)
    try:
        return await service.delete(get_entity_name(), target_menu_id, cache_name)
    except Exception as error:
        raise HTTPException(status_code=400, detail=error.args[0])
