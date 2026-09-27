"""Allow long book titles and author lists."""

from alembic import op
import sqlalchemy as sa


revision = "20260927_03"
down_revision = "20260927_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "books",
        "title",
        existing_type=sa.String(length=300),
        type_=sa.Text(),
        existing_nullable=False,
    )
    op.alter_column(
        "books",
        "author",
        existing_type=sa.String(length=300),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "books",
        "author",
        existing_type=sa.Text(),
        type_=sa.String(length=300),
        existing_nullable=False,
    )
    op.alter_column(
        "books",
        "title",
        existing_type=sa.Text(),
        type_=sa.String(length=300),
        existing_nullable=False,
    )