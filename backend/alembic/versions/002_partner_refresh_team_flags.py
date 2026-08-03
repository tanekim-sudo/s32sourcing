"""partner refresh settings, team shares, flags

Revision ID: 002_refresh_team_flags
Revises: 001_initial
Create Date: 2026-08-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_refresh_team_flags"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "partners",
        sa.Column("refresh_interval_hours", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "partners",
        sa.Column("last_refresh_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "team_shares",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("partner_id", sa.Integer(), sa.ForeignKey("partners.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("partner_id", "company_id", name="uq_team_share_partner_company"),
    )
    op.create_index("ix_team_shares_partner_id", "team_shares", ["partner_id"])
    op.create_index("ix_team_shares_company_id", "team_shares", ["company_id"])

    op.create_table(
        "company_flags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("partner_id", sa.Integer(), sa.ForeignKey("partners.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("flag", sa.String(32), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("partner_id", "company_id", name="uq_flag_partner_company"),
    )
    op.create_index("ix_company_flags_partner_id", "company_flags", ["partner_id"])
    op.create_index("ix_company_flags_company_id", "company_flags", ["company_id"])


def downgrade() -> None:
    op.drop_table("company_flags")
    op.drop_table("team_shares")
    op.drop_column("partners", "last_refresh_at")
    op.drop_column("partners", "refresh_interval_hours")
