import uuid
from dataclasses import dataclass, field, asdict
from enum import IntEnum
from typing import Any

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet


@dataclass
class BaseMenu:
    id: uuid.UUID
    title: str
    description: str

    def as_dict(self) -> dict[str, list[dict[str, Any]]]:
        return asdict(self)


@dataclass
class Menu(BaseMenu):
    pass


@dataclass
class Submenu(BaseMenu):
    menu_id: uuid.UUID


@dataclass
class Dish(BaseMenu):
    price: float
    discount: None | float = None
    submenu_id: uuid.UUID = None


@dataclass
class RestaurantMenu:
    menus: list[Menu] = field(default_factory=list)
    submenus: list[Submenu] = field(default_factory=list)
    dishes: list[Dish] = field(default_factory=list)


class ColumnMenu(IntEnum):
    ID = 1
    TITLE = 2
    DESCRIPTION = 3


class ColumnSubmenu(IntEnum):
    ID = 2
    TITLE = 3
    DESCRIPTION = 4


class ColumnDish(IntEnum):
    ID = 3
    TITLE = 4
    DESCRIPTION = 5
    PRICE = 6
    DISCOUNT = 7


class ParserXlsxService:
    def __init__(self) -> None:
        self.sheet:  Worksheet | None = None

    def load_sheet(self, path: str) -> None:
        self.sheet = load_workbook(filename=path, read_only=True).active

    def construct_entity(self,
                         entity_type: type[BaseMenu],
                         row: int,
                         column_type: type[IntEnum],
                         entity_id: uuid.UUID = None) -> BaseMenu | None:
        values = [self.sheet.cell(row=row, column=column).value for column in column_type]
        if not all(values[:-1]):
            return
        values[0] = uuid.uuid4().__str__()
        if entity_id:
            values.append(entity_id)
        return entity_type.__call__(*values)

    async def get_restaurant_menu(self) -> RestaurantMenu | None:
        restaurant_menu = RestaurantMenu()
        rows = iter(range(1, self.sheet.max_row + 1))
        menu_id, submenu_id = None, None
        for row in rows:
            if menu := self.construct_entity(Menu, row, ColumnMenu):
                menu_id = menu.id
                restaurant_menu.menus.append(menu)
                row = next(rows)
            if submenu := self.construct_entity(Submenu, row, ColumnSubmenu, menu_id):
                submenu_id = submenu.id
                restaurant_menu.submenus.append(submenu)
                row = next(rows)
            if dish := self.construct_entity(Dish, row, ColumnDish, submenu_id):
                restaurant_menu.dishes.append(dish)
        self.sheet = None
        return restaurant_menu
