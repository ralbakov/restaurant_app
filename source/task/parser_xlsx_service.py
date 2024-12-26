import asyncio
import uuid
from dataclasses import dataclass, field
from enum import IntEnum

from openpyxl import load_workbook
from openpyxl.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from database.schemas import BaseSchema, MenuCreation, SubmenuCreation, DishCreation


@dataclass
class RestaurantMenu:
    menu_id_to_menu: dict[str, MenuCreation] = field(default_factory=dict)
    menu_id_submenu_id_to_submenu: dict[tuple[str, ...], SubmenuCreation] = field(default_factory=dict)
    menu_id_submenu_id_dish_id_to_dish: dict[tuple[str, ...], DishCreation] = field(default_factory=dict)


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
        self.book: Workbook | None = None
        self.path: str | None = None

    async def load_sheet(self, path: str) -> None:
        self.path = path
        self.book = load_workbook(filename=path)
        self.sheet = self.book.active

    def construct_entity(self,
                         entity_type: type[BaseSchema],
                         row: int,
                         column_type: type[IntEnum],
                         entity_id: uuid.UUID = None) :
        cells = [self.sheet.cell(row=row, column=column) for column in column_type]
        values = [cell.value for cell in cells]
        if not all(values[:-1]):
            return

        if not self._check_uuid_4(values[0]):
            values[0] = uuid.uuid4()
            cells[0].value = str(values[0])
        if entity_id is not None:
            values.append(entity_id)
        keys = entity_type.model_fields.keys()
        return entity_type(**dict(zip(keys, values)))

    def get_restaurant_menu(self) -> RestaurantMenu | None:
        restaurant_menu = RestaurantMenu()
        rows = iter(range(1, self.sheet.max_row + 1))
        menu_id, submenu_id = None, None
        for row in rows:
            if menu := self.construct_entity(MenuCreation, row, ColumnMenu):
                menu_id = str(menu.id)
                restaurant_menu.menu_id_to_menu[menu_id] = menu
                row = next(rows)
            if menu_id and (submenu := self.construct_entity(SubmenuCreation, row, ColumnSubmenu, menu_id)):
                submenu_id = str(submenu.id)
                restaurant_menu.menu_id_submenu_id_to_submenu[(menu_id, submenu_id)] = submenu
                row = next(rows)
            if submenu_id and (dish := self.construct_entity(DishCreation, row, ColumnDish, submenu_id)):
                restaurant_menu.menu_id_submenu_id_dish_id_to_dish[(menu_id, submenu_id, str(dish.id))] = dish

        self.book.save(self.path)
        self.book.close()
        self.book = None
        self.sheet = None
        return restaurant_menu

    @staticmethod
    def _check_uuid_4(value: str) -> bool:
        try:
            uuid.UUID(value, version=4)
            return True
        except ValueError:
            return False

if __name__ == '__main__':
    async def main():
        parser = ParserXlsxService()
        await parser.load_sheet('../admin/Menu_2.xlsx')
        restaurant_menu = parser.get_restaurant_menu()
        for menu_id, submenu_id in restaurant_menu.menu_id_submenu_id_to_submenu:
            print(menu_id, submenu_id)
        print()
        for menu_id, submenu_id, _ in restaurant_menu.menu_id_submenu_id_dish_id_to_dish:
            print(menu_id, submenu_id)
    asyncio.run(main())