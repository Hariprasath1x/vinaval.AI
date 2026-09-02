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
    # No-op: the original migration (f2b3c4d5e6f7) was corrected to
    # create the user_id column as Integer directly for a fresh PostgreSQL DB.
    pass


def downgrade() -> None:
    pass

