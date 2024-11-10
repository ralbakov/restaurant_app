from fastapi import APIRouter, Depends, HTTPException

from database.models import Dish as Entity
from database.schemas import Dish, DishCreation, DishUpdation
from service.restaurant_menu_service import RestaurantMenuService, RedisCacheName

dish_router = APIRouter(prefix='/api/v1/menus/{target_menu_id}/submenus/{target_submenu_id}/dishes', tags=['Dish'])


def get_entity_name() -> str:
    return Entity.__name__.lower()


@dish_router.post('', name='Create dish', status_code=201, response_model=Dish)
async def create(
        target_menu_id: str,
        target_submenu_id: str,
        creation_schema: DishCreation,
        service: RestaurantMenuService=Depends()
):
    identification = RedisCacheName(menu_id=target_menu_id, submenu_id=target_submenu_id)
    try:
        return await service.create(get_entity_name(), creation_schema, identification)
    except Exception as error:
        raise HTTPException(status_code=400, detail=error.args[0])


@dish_router.get('', name='Get all dish', status_code=200, response_model=list[Dish])
async def read_all(
        target_menu_id: str,
        target_submenu_id: str,
        service: RestaurantMenuService=Depends()
):
    identification = RedisCacheName(menu_id=target_menu_id, submenu_id=target_submenu_id)
    return await service.read_all(get_entity_name(), identification)


@dish_router.get('/{target_dish_id}', name='Get one dish', status_code=200, response_model=Dish)
async def read_one(
        target_menu_id: str,
        target_submenu_id: str,
        target_dish_id: str,
        service: RestaurantMenuService=Depends()
):
    identification = RedisCacheName(menu_id=target_menu_id, submenu_id=target_submenu_id, dish_id=target_dish_id)
    try:
        return await service.read_one(get_entity_name(), target_dish_id, identification)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=error.args[0])


@dish_router.patch('/{target_dish_id}', name='Update dish', status_code=200, response_model=Dish)
async def update(
        target_menu_id: str,
        target_submenu_id: str,
        target_dish_id: str,
        updation_schema: DishUpdation,
        service: RestaurantMenuService=Depends()
):
    identification = RedisCacheName(menu_id=target_menu_id, submenu_id=target_submenu_id, dish_id=target_dish_id)
    try:
        return await service.update(get_entity_name(), target_dish_id, updation_schema, identification)
    except Exception as error:
        raise error


@dish_router.delete('/{target_dish_id}', name='Delete dish', status_code=200, response_model=None)
async def delete(
        target_menu_id: str,
        target_submenu_id: str,
        target_dish_id: str,
        service: RestaurantMenuService=Depends()
):
    identification = RedisCacheName(menu_id=target_menu_id, submenu_id=target_submenu_id, dish_id=target_dish_id)
    try:
        return await service.delete(get_entity_name(), target_dish_id, identification)
    except Exception as error:
        raise HTTPException(status_code=404, detail=error.args[0])
