"""add learning spaces, chat messages, space notes

Revision ID: a3f8c21d5e90
Revises: 7515a35da012
Create Date: 2026-07-07 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f8c21d5e90'
down_revision: Union[str, None] = '7515a35da012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── learning_spaces ────────────────────────────────────────────────────
    op.create_table(
        'learning_spaces',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('exam_id', sa.String(), nullable=False),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_learning_spaces_id'), 'learning_spaces', ['id'], unique=False)
    op.create_index(op.f('ix_learning_spaces_user_id'), 'learning_spaces', ['user_id'], unique=False)

    # ── chat_messages ──────────────────────────────────────────────────────
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('space_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=16), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['space_id'], ['learning_spaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_chat_messages_id'), 'chat_messages', ['id'], unique=False)
    op.create_index(op.f('ix_chat_messages_space_id'), 'chat_messages', ['space_id'], unique=False)

    # ── space_notes ────────────────────────────────────────────────────────
    op.create_table(
        'space_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('space_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['space_id'], ['learning_spaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('space_id'),
    )
    op.create_index(op.f('ix_space_notes_id'), 'space_notes', ['id'], unique=False)
    op.create_index(op.f('ix_space_notes_space_id'), 'space_notes', ['space_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_space_notes_space_id'), table_name='space_notes')
    op.drop_index(op.f('ix_space_notes_id'), table_name='space_notes')
    op.drop_table('space_notes')

    op.drop_index(op.f('ix_chat_messages_space_id'), table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_id'), table_name='chat_messages')
    op.drop_table('chat_messages')

    op.drop_index(op.f('ix_learning_spaces_user_id'), table_name='learning_spaces')
    op.drop_index(op.f('ix_learning_spaces_id'), table_name='learning_spaces')
    op.drop_table('learning_spaces')
