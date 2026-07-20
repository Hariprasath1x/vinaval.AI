"""add hashed_password and make google_id nullable

Revision ID: add_user_auth_fields
Revises: add_doc_source
Create Date: 2026-07-16
"""
from alembic import op
import sqlalchemy as sa

revision = 'add_user_auth_fields'
down_revision = 'add_doc_source'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make google_id nullable (was NOT NULL, now supports email/pw users)
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('google_id', nullable=True)
        batch_op.add_column(sa.Column('hashed_password', sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('hashed_password')
        batch_op.alter_column('google_id', nullable=False)
