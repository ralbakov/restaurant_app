from decimal import Decimal

from pydantic import UUID4, BaseModel, Field, ConfigDict


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MenuBase(Schema):
    title: str
    description: str | None


class Menu(MenuBase):
    id: UUID4
    submenus_count: int
    dishes_count: int


class MenuCreation(MenuBase):
    pass


class MenuUpdation(MenuBase):
    pass


class SubmenuBase(Schema):
    title: str
    description: str | None


class Submenu(SubmenuBase):
    id: UUID4
    menu_id: UUID4
    dishes_count: int


class SubmenuCreation(SubmenuBase):
    pass


class SubmenuUpdation(SubmenuBase):
    pass


class DishBase(Schema):
    title: str
    description: str | None
    price: Decimal = Field(decimal_places=2)


    # @field_validator('discount')
    # def validate_discount(cls, value: int) -> int:
    #     """Валидация скидки."""
    #     if value > 100 or value < 0:
    #         raise ValueError(
    #             'Скидка должна находиться в диапазоне от 0 до 100'
    #         )
    #     return value


class Dish(DishBase):
    id: UUID4
    submenu_id: UUID4


class DishCreation(DishBase):   
    pass


class DishUpdation(DishBase):
    pass
