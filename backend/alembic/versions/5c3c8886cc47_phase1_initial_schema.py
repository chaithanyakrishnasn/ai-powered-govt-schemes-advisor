"""phase1_initial_schema

Revision ID: 5c3c8886cc47
Revises:
Create Date: 2026-05-03 15:05:05.511060

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "5c3c8886cc47"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Extensions must be created before any vector column
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    op.create_table(
        "schemes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ministry", sa.Text(), nullable=True),
        sa.Column("level", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column(
            "categories",
            sa.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("benefit_type", sa.Text(), nullable=True),
        sa.Column("benefit_amount_min", sa.Numeric(), nullable=True),
        sa.Column("benefit_amount_max", sa.Numeric(), nullable=True),
        sa.Column("benefit_description", sa.Text(), nullable=True),
        sa.Column("application_url", sa.Text(), nullable=True),
        sa.Column("application_mode", sa.Text(), nullable=True),
        sa.Column(
            "documents_required",
            sa.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("raw_eligibility_text", sa.Text(), nullable=True),
        sa.Column("search_text", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_scraped_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_updated", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("level IN ('central', 'state')", name="level"),
        sa.CheckConstraint(
            "benefit_type IN ('cash','subsidy','insurance','loan','training','pension','scholarship','other')",
            name="benefit_type",
        ),
        sa.CheckConstraint(
            "application_mode IN ('online','offline','both')",
            name="application_mode",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_schemes"),
        sa.UniqueConstraint("slug", name="uq_schemes_slug"),
    )

    op.create_table(
        "user_profiles",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("gender", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("district", sa.Text(), nullable=True),
        sa.Column("annual_income", sa.Numeric(), nullable=True),
        sa.Column("occupation", sa.Text(), nullable=True),
        sa.Column("caste_category", sa.Text(), nullable=True),
        sa.Column("religion", sa.Text(), nullable=True),
        sa.Column("is_farmer", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("land_holding_acres", sa.Numeric(), nullable=True),
        sa.Column("education_level", sa.Text(), nullable=True),
        sa.Column("marital_status", sa.Text(), nullable=True),
        sa.Column("family_size", sa.Integer(), nullable=True),
        sa.Column("has_disability", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("disability_percentage", sa.Integer(), nullable=True),
        sa.Column("employment_status", sa.Text(), nullable=True),
        sa.Column(
            "preferred_language",
            sa.Text(),
            server_default=sa.text("'en'"),
            nullable=False,
        ),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "gender IN ('male','female','other','prefer_not_to_say')",
            name="gender",
        ),
        sa.CheckConstraint(
            "caste_category IN ('GEN','OBC','SC','ST','EWS')",
            name="caste_category",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_profiles"),
    )

    op.create_table(
        "eligibility_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scheme_id", sa.Integer(), nullable=False),
        sa.Column("rule_type", sa.Text(), nullable=False),
        sa.Column("operator", sa.Text(), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("logic_group", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "group_operator",
            sa.Text(),
            server_default=sa.text("'AND'"),
            nullable=False,
        ),
        sa.Column("is_required", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "operator IN ('eq','neq','lt','lte','gt','gte','in','not_in','between','exists','any_of','all_of')",
            name="operator",
        ),
        sa.CheckConstraint(
            "group_operator IN ('AND','OR')",
            name="group_operator",
        ),
        sa.ForeignKeyConstraint(
            ["scheme_id"],
            ["schemes.id"],
            name="fk_eligibility_rules_scheme_id_schemes",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_eligibility_rules"),
    )

    op.create_table(
        "scheme_matches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("scheme_id", sa.Integer(), nullable=False),
        sa.Column("match_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("eligibility_status", sa.Text(), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("matched_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "matched_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "eligibility_status IN ('eligible','likely_eligible','need_more_info','not_eligible')",
            name="eligibility_status",
        ),
        sa.ForeignKeyConstraint(
            ["scheme_id"],
            ["schemes.id"],
            name="fk_scheme_matches_scheme_id_schemes",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user_profiles.id"],
            name="fk_scheme_matches_user_id_user_profiles",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_scheme_matches"),
    )

    op.create_table(
        "scheme_translations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scheme_id", sa.Integer(), nullable=False),
        sa.Column("language", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("benefit_description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "language IN ('hi','kn','ta','te','mr','bn')",
            name="language",
        ),
        sa.ForeignKeyConstraint(
            ["scheme_id"],
            ["schemes.id"],
            name="fk_scheme_translations_scheme_id_schemes",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_scheme_translations"),
        sa.UniqueConstraint(
            "scheme_id", "language", name="uq_scheme_translations_scheme_id_language"
        ),
    )

    # Standard B-tree indexes
    op.create_index("idx_schemes_level_state", "schemes", ["level", "state"])
    op.create_index(
        "idx_schemes_categories", "schemes", ["categories"], postgresql_using="gin"
    )
    op.create_index("idx_elig_scheme", "eligibility_rules", ["scheme_id"])
    op.create_index("idx_elig_rule_type", "eligibility_rules", ["rule_type"])

    # Composite with DESC — use raw SQL
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_matches_user "
        "ON scheme_matches (user_id, matched_at DESC)"
    )

    # IVFFlat vector index — rebuild after bulk insert for optimal recall
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_schemes_embedding "
        "ON schemes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    # GIN full-text index on search_text
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_schemes_search_text "
        "ON schemes USING gin (to_tsvector('english', coalesce(search_text, '')))"
    )


def downgrade() -> None:
    op.drop_table("scheme_translations")
    op.drop_table("scheme_matches")
    op.drop_table("eligibility_rules")
    op.drop_table("user_profiles")
    op.drop_table("schemes")
    op.execute("DROP EXTENSION IF EXISTS vector;")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto;")
