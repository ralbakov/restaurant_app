from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from core.config import settings
from database.schemas import Dish, DishCreation, DishUpdation
from service.restaurant_service import RestaurantService, TargetCode


path = settings.url

dish_router = APIRouter(prefix=path.target_dishes, tags=['Dish'])


@dish_router.post('', name='Create dish', status_code=201, response_model=Dish)
async def create(target_menu_id: str,
                 target_submenu_id: str,
                 creation_schema: DishCreation,
                 task: BackgroundTasks,
                 service: RestaurantService=Depends()):
    target_code = TargetCode.construct_entity_name(Dish)
    target_code.menu = target_menu_id
    target_code.submenu = target_submenu_id
    try:
        return await service.create(creation_schema, target_code, task)
    except Exception as error:
        raise HTTPException(status_code=400, detail=error.args[0])


@dish_router.get('', name='Get all dish', status_code=200, response_model=list[Dish])
async def read_all(target_menu_id: str,
                   target_submenu_id: str,
                   task: BackgroundTasks,
                   service: RestaurantService = Depends()):
    target_code = TargetCode.construct_entity_name(Dish)
    target_code.menu = target_menu_id
    target_code.submenu = target_submenu_id
    return await service.read_all(target_code, task)


@dish_router.get(path.target_dish_id, name='Get one dish', status_code=200, response_model=Dish)
async def read_one(target_menu_id: str,
                   target_submenu_id: str,
                   target_dish_id: str,
                   task: BackgroundTasks,
                   service: RestaurantService = Depends()):
    target_code = TargetCode.construct_entity_name(Dish)
    target_code.menu = target_menu_id
    target_code.submenu = target_submenu_id
    target_code.dish = target_dish_id
    try:
        return await service.read_one(target_code, task)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=error.args[0])


@dish_router.patch(path.target_dish_id, name='Update dish', status_code=200, response_model=Dish)
async def update(target_menu_id: str,
                 target_submenu_id: str,
                 target_dish_id: str,
                 updation_schema: DishUpdation,
                 task: BackgroundTasks,
                 service: RestaurantService=Depends()):
    target_code = TargetCode.construct_entity_name(Dish)
    target_code.menu = target_menu_id
    target_code.submenu = target_submenu_id
    target_code.dish = target_dish_id
    try:
        return await service.update(updation_schema, target_code, task)
    except Exception as error:
        raise error


@dish_router.delete(path.target_dish_id, name='Delete dish', status_code=200, response_model=None)
async def delete(target_menu_id: str,
                 target_submenu_id: str,
                 target_dish_id: str,
                 task: BackgroundTasks,
                 service: RestaurantService=Depends()):
    target_code = TargetCode.construct_entity_name(Dish)
    target_code.menu = target_menu_id
    target_code.submenu = target_submenu_id
    target_code.dish = target_dish_id
    try:
        return await service.delete(target_code, task)
    except Exception as error:
        raise HTTPException(status_code=404, detail=error.args[0])
