from decimal import Decimal
from typing import Optional, Self

from pydantic import UUID4, BaseModel, Field, ConfigDict, field_validator, model_validator


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Identification(Schema):
    id: Optional[UUID4] = None


class MenuBase(Schema):
    title: str
    description: str | None


class Menu(MenuBase, Identification):
    submenus_count: int
    dishes_count: int


class MenuCreation(MenuBase, Identification):
    pass


class MenuUpdation(MenuBase):
    pass


class SubmenuBase(Schema):
    title: str
    description: str | None


class Submenu(SubmenuBase, Identification):
    menu_id: UUID4
    dishes_count: int


class SubmenuCreation(SubmenuBase, Identification):
    pass


class SubmenuUpdation(SubmenuBase):
    pass


class DishBase(Schema):
    title: str
    description: str | None
    price: Decimal = Field(decimal_places=2)
    discount: Optional[int] = None

    @field_validator('discount') # noqa
    @classmethod
    def validate_discount(cls, discount: int | None) -> int | None:
        if discount is None or 0 <= discount < 100:
            return discount
        raise ValueError('Размер скидки не может быть отрицательным или больше 100')


class Dish(DishBase, Identification):
    submenu_id: UUID4

    @model_validator(mode='after')
    def get_price_with_discount(self) -> Self:
        if discount := self.discount:
            self.price = (self.price * Decimal(1 - discount / 100)).quantize(Decimal("1.00"))
        else:
            self.discount = 0
        return self


class DishCreation(DishBase, Identification):
    pass


class DishUpdation(DishBase):
    pass
