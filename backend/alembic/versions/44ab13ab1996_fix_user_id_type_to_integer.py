"""fix_user_id_type_to_integer

Revision ID: 44ab13ab1996
Revises: e1a2b3c4d5f6
Create Date: 2026-08-11 21:24:32.336096

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '44ab13ab1996'
down_revision: Union[str, None] = 'e1a2b3c4d5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite doesn't support ALTER COLUMN, so use batch mode
    with op.batch_alter_table('quiz_sessions', schema=None) as batch_op:
        batch_op.alter_column(
            'user_id',
            existing_type=sa.String(),
            type_=sa.Integer(),
            existing_nullable=True
        )
        batch_op.create_index(op.f('ix_quiz_sessions_user_id'), ['user_id'], unique=False)

    with op.batch_alter_table('performance_analyses', schema=None) as batch_op:
        batch_op.alter_column(
            'user_id',
            existing_type=sa.String(),
            type_=sa.Integer(),
            existing_nullable=True
        )
        batch_op.drop_constraint('uq_performance_analyses_session_id', type_='unique')


def downgrade() -> None:
    with op.batch_alter_table('performance_analyses', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_performance_analyses_session_id', ['session_id'])
        batch_op.alter_column(
            'user_id',
            existing_type=sa.Integer(),
            type_=sa.String(),
            existing_nullable=True
        )

    with op.batch_alter_table('quiz_sessions', schema=None) as batch_op:
        batch_op.drop_index(op.f('ix_quiz_sessions_user_id'))
        batch_op.alter_column(
            'user_id',
            existing_type=sa.Integer(),
            type_=sa.String(),
            existing_nullable=True
        )

