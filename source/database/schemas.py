from decimal import Decimal
from typing import Optional, Self

from pydantic import UUID4, BaseModel, Field, ConfigDict, field_validator, model_validator


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    description: str | None


class Identification(BaseModel):
    id: Optional[UUID4] = None


class Menu(BaseSchema, Identification):
    submenus_count: Optional[int] = None
    dishes_count: Optional[int] = None


class MenuCreation(BaseSchema, Identification):
    pass


class MenuUpdation(BaseSchema):
    pass


class Submenu(BaseSchema, Identification):
    menu_id: UUID4
    dishes_count: Optional[int] = None


class SubmenuCreation(BaseSchema, Identification):
    pass


class SubmenuUpdation(BaseSchema):
    pass


class DishBase(BaseSchema):
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
