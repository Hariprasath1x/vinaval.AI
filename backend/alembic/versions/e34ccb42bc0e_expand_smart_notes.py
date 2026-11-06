"""expand_smart_notes

Revision ID: e34ccb42bc0e
Revises: 9799ba135d56
Create Date: 2026-11-06 14:21:53.109246

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e34ccb42bc0e'
down_revision: Union[str, None] = '9799ba135d56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    naming_convention = {"uq": "uq_%(table_name)s_%(column_0_name)s"}
    with op.batch_alter_table('space_notes', schema=None, naming_convention=naming_convention) as batch_op:
        batch_op.drop_constraint('uq_space_notes_space_id', type_='unique')
        batch_op.drop_index('ix_space_notes_space_id')
        batch_op.create_index(batch_op.f('ix_space_notes_space_id'), ['space_id'], unique=False)
        batch_op.add_column(sa.Column('title', sa.String(length=255), nullable=False, server_default='Untitled Note'))
        batch_op.add_column(sa.Column('topic', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('source_type', sa.String(length=50), nullable=False, server_default='manual'))
        batch_op.add_column(sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_space_notes_user_id'), ['user_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('space_notes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_space_notes_user_id'))
        batch_op.drop_column('user_id')
        batch_op.drop_column('created_at')
        batch_op.drop_column('source_type')
        batch_op.drop_column('topic')
        batch_op.drop_column('title')
        batch_op.drop_index(batch_op.f('ix_space_notes_space_id'))
        batch_op.create_index('ix_space_notes_space_id', ['space_id'], unique=True)
        batch_op.create_unique_constraint('uq_space_notes_space_id', ['space_id'])

