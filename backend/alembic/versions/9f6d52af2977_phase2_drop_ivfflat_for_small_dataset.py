"""phase2_drop_ivfflat_for_small_dataset

Revision ID: 9f6d52af2977
Revises: 5c3c8886cc47
Create Date: 2026-05-04 13:38:25.987673

IVFFlat with lists=100 on 334 rows is actively harmful — each list has ~3 vectors,
so probes return very few candidates and recall suffers badly. Sequential scan on
334 rows is <10ms and gives perfect recall.

TODO: Add HNSW index when scheme count exceeds 1K rows.
  HNSW is preferred over IVFFlat for production at this dataset's eventual size:
  CREATE INDEX idx_schemes_embedding ON schemes USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
"""

from collections.abc import Sequence

from alembic import op

revision: str = "9f6d52af2977"
down_revision: str | Sequence[str] | None = "5c3c8886cc47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_schemes_embedding")


def downgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_schemes_embedding "
        "ON schemes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
