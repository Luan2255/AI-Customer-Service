"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
# Import migration operations and schema types used by generated revision code.
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
# Revision links let Alembic order and traverse the migration history.
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Apply the generated schema changes."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Reverse the generated schema changes when rolling back this revision."""
    ${downgrades if downgrades else "pass"}