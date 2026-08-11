"""add chat_sessions table and session_id to chat_messages

Revision ID: e1a2b3c4d5f6
Revises: f2b3c4d5e6f7
Create Date: 2026-08-11 09:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1a2b3c4d5f6'
down_revision: Union[str, None] = 'f2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── chat_sessions ──────────────────────────────────────────────────────
    op.create_table(
        'chat_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('space_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False, server_default='New Chat'),
        sa.Column('ai_suggested_name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['space_id'], ['learning_spaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_chat_sessions_id'), 'chat_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_chat_sessions_space_id'), 'chat_sessions', ['space_id'], unique=False)

    # ── Add session_id FK to chat_messages (nullable for backward compat) ──
    with op.batch_alter_table('chat_messages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('session_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_chat_messages_session_id'), ['session_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_chat_messages_session_id',
            'chat_sessions',
            ['session_id'], ['id'],
            ondelete='CASCADE'
        )


def downgrade() -> None:
    with op.batch_alter_table('chat_messages', schema=None) as batch_op:
        batch_op.drop_constraint('fk_chat_messages_session_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_chat_messages_session_id'))
        batch_op.drop_column('session_id')

    op.drop_index(op.f('ix_chat_sessions_space_id'), table_name='chat_sessions')
    op.drop_index(op.f('ix_chat_sessions_id'), table_name='chat_sessions')
    op.drop_table('chat_sessions')
