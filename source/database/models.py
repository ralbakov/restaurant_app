import uuid

from sqlalchemy import DECIMAL, ForeignKey, String, func, select, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, column_property


class Base(DeclarativeBase):
    id: Mapped[uuid.UUID]
    pass


class Dish(Base):
    __tablename__ = 'dish'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[str] = mapped_column(DECIMAL(scale=2), nullable=False)
    discount: Mapped[int] = mapped_column(Integer, nullable=True)
    submenu_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('submenu.id', ondelete='cascade'))
    submenu: Mapped['Submenu'] = relationship(back_populates='dish')


class Submenu(Base):
    __tablename__ = 'submenu'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    menu_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('menu.id', ondelete='cascade'))
    dish: Mapped['Dish'] = relationship(back_populates='submenu')
    menu: Mapped['Menu'] = relationship(back_populates='submenu')
    dishes_count = column_property(
        select(func.count(Dish.id)).where(Dish.submenu_id == id).correlate_except(Dish).as_scalar()
    )


class Menu(Base):
    __tablename__ = 'menu'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    submenu: Mapped['Submenu'] = relationship(back_populates='menu', cascade='all, delete')
    submenus_count = column_property(
        select(func.count(Submenu.id)).where(Submenu.menu_id == id).correlate_except(Submenu).scalar_subquery()
    )
    dishes_count = column_property(
        select(func.count(Dish.id)).
        where(Dish.submenu_id == (select(Submenu.id).where(Submenu.menu_id == id)).scalar_subquery()).
        correlate_except(Dish).scalar_subquery()
    )
