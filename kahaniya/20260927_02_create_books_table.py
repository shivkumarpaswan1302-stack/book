"""Create books table for the catalog."""

from alembic import op
import sqlalchemy as sa


revision = "20260927_02"
down_revision = "20260927_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "books",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("author", sa.String(length=300), nullable=False),
        sa.Column("isbn", sa.String(length=20), nullable=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("genres", sa.JSON(), nullable=False),
        sa.Column("themes", sa.JSON(), nullable=False),
        sa.Column("moods", sa.JSON(), nullable=False),
        sa.Column("intents", sa.JSON(), nullable=False),
        sa.Column("intensity", sa.Integer(), nullable=False),
        sa.Column("complexity", sa.Integer(), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("pace", sa.String(length=40), nullable=False),
        sa.Column("description", sa.String(length=600), nullable=False),
        sa.Column("tone", sa.String(length=200), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("badge", sa.String(length=80), nullable=False),
        sa.Column("color", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_books_kind", "books", ["kind"])


def downgrade() -> None:
    op.drop_index("ix_books_kind", table_name="books")
    op.drop_table("books")
