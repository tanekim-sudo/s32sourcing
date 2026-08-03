"""initial multi-partner schema

Revision ID: 001_initial
Revises:
Create Date: 2026-08-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

partner_role = postgresql.ENUM("partner", "admin", name="partner_role", create_type=False)


def upgrade() -> None:
    partner_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "partners",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("clerk_user_id", sa.String(255), nullable=True),
        sa.Column("role", partner_role, nullable=False, server_default="partner"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_partners_email", "partners", ["email"], unique=True)
    op.create_index("ix_partners_clerk_user_id", "partners", ["clerk_user_id"], unique=True)

    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("domain", sa.String(512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("affinity_org_id", sa.Integer(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_companies_name", "companies", ["name"])
    op.create_index("ix_companies_domain", "companies", ["domain"], unique=True)
    op.create_index("ix_companies_affinity_org_id", "companies", ["affinity_org_id"], unique=True)

    op.create_table(
        "thesis_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("partner_id", sa.Integer(), sa.ForeignKey("partners.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("keywords", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("exa_queries", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("github_topics", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_thesis_configs_partner_id", "thesis_configs", ["partner_id"])

    op.create_table(
        "people",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("linkedin_url", sa.String(1024), nullable=True),
        sa.Column("affinity_person_id", sa.Integer(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_people_company_id", "people", ["company_id"])
    op.create_index("ix_people_email", "people", ["email"])
    op.create_index("ix_people_linkedin_url", "people", ["linkedin_url"], unique=True)
    op.create_index("ix_people_affinity_person_id", "people", ["affinity_person_id"], unique=True)

    op.create_table(
        "signals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("external_id", sa.String(512), nullable=True),
        sa.Column("title", sa.String(1024), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("url", sa.String(2048), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("matched_thesis_config_ids", postgresql.ARRAY(sa.Integer()), nullable=False, server_default="{}"),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_signals_company_id", "signals", ["company_id"])
    op.create_index("ix_signals_source", "signals", ["source"])
    op.create_index("ix_signals_external_id", "signals", ["external_id"])

    op.create_table(
        "watchlist_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("partner_id", sa.Integer(), sa.ForeignKey("partners.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("partner_id", "company_id", name="uq_watchlist_partner_company"),
    )
    op.create_index("ix_watchlist_entries_partner_id", "watchlist_entries", ["partner_id"])
    op.create_index("ix_watchlist_entries_company_id", "watchlist_entries", ["company_id"])

    op.create_table(
        "rubric_base",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("yaml_content", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("partners.id"), nullable=True),
        sa.Column("changelog", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_rubric_base_version", "rubric_base", ["version"], unique=True)
    op.create_index("ix_rubric_base_is_active", "rubric_base", ["is_active"])

    op.create_table(
        "rubric_overlays",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("partner_id", sa.Integer(), sa.ForeignKey("partners.id"), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("base_rubric_version", sa.String(64), nullable=False),
        sa.Column(
            "weight_adjustments",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "added_dimensions",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("partner_id", "version", name="uq_overlay_partner_version"),
    )
    op.create_index("ix_rubric_overlays_partner_id", "rubric_overlays", ["partner_id"])

    op.create_table(
        "scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("rubric_base_version", sa.String(64), nullable=False),
        sa.Column("total_score", sa.Float(), nullable=False),
        sa.Column("subscores", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("evidence", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("why_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("company_id", "rubric_base_version", name="uq_score_company_base_version"),
    )
    op.create_index("ix_scores_company_id", "scores", ["company_id"])
    op.create_index("ix_scores_rubric_base_version", "scores", ["rubric_base_version"])

    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("partner_id", sa.Integer(), sa.ForeignKey("partners.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("thumbs", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("partner_id", "company_id", name="uq_feedback_partner_company"),
    )
    op.create_index("ix_feedback_partner_id", "feedback", ["partner_id"])
    op.create_index("ix_feedback_company_id", "feedback", ["company_id"])


def downgrade() -> None:
    op.drop_table("feedback")
    op.drop_table("scores")
    op.drop_table("rubric_overlays")
    op.drop_table("rubric_base")
    op.drop_table("watchlist_entries")
    op.drop_table("signals")
    op.drop_table("people")
    op.drop_table("thesis_configs")
    op.drop_table("companies")
    op.drop_table("partners")
    partner_role.drop(op.get_bind(), checkfirst=True)
