from decimal import Decimal

from pydantic import UUID4, BaseModel, Field, ConfigDict, field_validator, model_validator
from typing_extensions import Self


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
    discount: int | None = Field(default=None)

    @field_validator('discount') # noqa
    @classmethod
    def validate_discount(cls, discount: int | None) -> int | None:
        if discount is None or 0 <= discount < 100:
            return discount
        raise ValueError('Размер скидки не может быть отрицательным или больше 100')


class Dish(DishBase):
    id: UUID4
    submenu_id: UUID4

    @model_validator(mode='after')
    def get_price_with_discount(self) -> Self:
        if discount := self.discount:
            self.price = (self.price * Decimal(1 - discount / 100)).quantize(Decimal("1.00"))
        return self


class DishCreation(DishBase):
    pass


class DishUpdation(DishBase):
    pass
