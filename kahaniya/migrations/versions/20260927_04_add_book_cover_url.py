"""Add optional cover image URLs to books."""

from alembic import op
import sqlalchemy as sa


revision = "20260927_04"
down_revision = "20260927_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("books", sa.Column("cover_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("books", "cover_url")