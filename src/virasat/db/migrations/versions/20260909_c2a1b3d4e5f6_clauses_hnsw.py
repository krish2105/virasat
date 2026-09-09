"""clauses hnsw index

Revision ID: c2a1b3d4e5f6
Revises: b1fd1e47ebc2
Create Date: 2026-09-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c2a1b3d4e5f6"
down_revision: str | None = "b1fd1e47ebc2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX clauses_embedding_hnsw ON clauses USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS clauses_embedding_hnsw")
