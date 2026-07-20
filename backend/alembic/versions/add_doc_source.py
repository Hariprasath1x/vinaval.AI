"""add source column to space_documents

Revision ID: add_doc_source
Revises: 
Create Date: 2026-07-16

"""
from alembic import op
import sqlalchemy as sa

revision = 'add_doc_source'
down_revision = 'f059c1b9b792'  # add_documents (last migration)
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'space_documents',
        sa.Column('source', sa.String(), nullable=False, server_default='user_upload')
    )


def downgrade() -> None:
    op.drop_column('space_documents', 'source')
