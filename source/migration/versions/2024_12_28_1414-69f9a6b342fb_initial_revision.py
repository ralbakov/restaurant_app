"""Initial revision

Revision ID: 69f9a6b342fb
Revises: 
Create Date: 2024-12-28 14:14:35.892077

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '69f9a6b342fb'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('menu',
                    sa.Column('id', sa.UUID(), nullable=False),
                    sa.Column('title', sa.String(), nullable=False),
                    sa.Column('description', sa.String(), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('title'),
    )
    op.create_table('submenu',
                    sa.Column('id', sa.UUID(), nullable=False),
                    sa.Column('title', sa.String(), nullable=False),
                    sa.Column('description', sa.String(), nullable=False),
                    sa.Column('menu_id', sa.UUID(), nullable=False),
                    sa.ForeignKeyConstraint(['menu_id'], ['menu.id'], ondelete='cascade'),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('title'),
                    )
    op.create_table('dish',
                    sa.Column('id', sa.UUID(), nullable=False),
                    sa.Column('title', sa.String(), nullable=False),
                    sa.Column('description', sa.String(), nullable=False),
                    sa.Column('price', sa.DECIMAL(scale=2), nullable=False),
                    sa.Column('discount', sa.Integer(), nullable=True),
                    sa.Column('submenu_id', sa.UUID(), nullable=False),
                    sa.ForeignKeyConstraint(['submenu_id'], ['submenu.id'], ondelete='cascade'),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('title'),
    )


def downgrade() -> None:
    op.drop_table('dish')
    op.drop_table('submenu')
    op.drop_table('menu')
