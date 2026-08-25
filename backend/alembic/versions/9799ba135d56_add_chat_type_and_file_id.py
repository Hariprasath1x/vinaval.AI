"""Add chat_type and file_id

Revision ID: 9799ba135d56
Revises: a636d90fd135
Create Date: 2026-08-25 10:01:41.234236

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9799ba135d56'
down_revision: Union[str, None] = 'a636d90fd135'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('chat_sessions') as batch_op:
        batch_op.add_column(sa.Column('chat_type', sa.String(length=50), nullable=False, server_default='AI_TUTOR'))
    with op.batch_alter_table('chat_sessions') as batch_op:
        batch_op.add_column(sa.Column('file_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_chat_sessions_file_id', 'space_documents', ['file_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    with op.batch_alter_table('chat_sessions') as batch_op:
        batch_op.drop_constraint('fk_chat_sessions_file_id', type_='foreignkey')
        batch_op.drop_column('file_id')
        batch_op.drop_column('chat_type')
