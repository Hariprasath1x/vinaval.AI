"""add topics and chunk_count to space_documents"""
from alembic import op
import sqlalchemy as sa

revision = "e1a2b3c4d5e6"
down_revision = "d3c2a1b9c792"   # add quiz sessions (true head before this)
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("space_documents") as batch_op:
        batch_op.add_column(sa.Column("topics", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("chunk_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("space_documents") as batch_op:
        batch_op.drop_column("chunk_count")
        batch_op.drop_column("topics")
