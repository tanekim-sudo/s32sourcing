from __future__ import annotations

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PartnerRole(str, enum.Enum):
    partner = "partner"
    admin = "admin"


class Partner(Base):
    __tablename__ = "partners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    clerk_user_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)
    role: Mapped[PartnerRole] = mapped_column(
        Enum(PartnerRole, name="partner_role"),
        nullable=False,
        default=PartnerRole.partner,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    thesis_configs: Mapped[List["ThesisConfig"]] = relationship(back_populates="partner")
    watchlist_entries: Mapped[List["WatchlistEntry"]] = relationship(back_populates="partner")
    rubric_overlays: Mapped[List["RubricOverlay"]] = relationship(back_populates="partner")
    feedback: Mapped[List["Feedback"]] = relationship(back_populates="partner")


class ThesisConfig(Base):
    __tablename__ = "thesis_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # null partner_id = firm-wide / shared thesis area
    partner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("partners.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    keywords: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    exa_queries: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    github_topics: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    partner: Mapped[Optional["Partner"]] = relationship(back_populates="thesis_configs")


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    domain: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    affinity_org_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, unique=True, index=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    people: Mapped[List["Person"]] = relationship(back_populates="company")
    signals: Mapped[List["Signal"]] = relationship(back_populates="company")
    scores: Mapped[List["Score"]] = relationship(back_populates="company")
    watchlist_entries: Mapped[List["WatchlistEntry"]] = relationship(back_populates="company")
    feedback: Mapped[List["Feedback"]] = relationship(back_populates="company")


class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True, unique=True)
    affinity_person_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, unique=True, index=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped[Optional["Company"]] = relationship(back_populates="people")


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Which partner/shared thesis configs this signal matched
    matched_thesis_config_ids: Mapped[list] = mapped_column(ARRAY(Integer), nullable=False, default=list)
    observed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped[Optional["Company"]] = relationship(back_populates="signals")


class WatchlistEntry(Base):
    __tablename__ = "watchlist_entries"
    __table_args__ = (UniqueConstraint("partner_id", "company_id", name="uq_watchlist_partner_company"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id"), nullable=False, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    partner: Mapped["Partner"] = relationship(back_populates="watchlist_entries")
    company: Mapped["Company"] = relationship(back_populates="watchlist_entries")


class RubricBase(Base):
    __tablename__ = "rubric_base"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    yaml_content: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("partners.id"), nullable=True)
    changelog: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RubricOverlay(Base):
    __tablename__ = "rubric_overlays"
    __table_args__ = (
        UniqueConstraint("partner_id", "version", name="uq_overlay_partner_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    base_rubric_version: Mapped[str] = mapped_column(String(64), nullable=False)
    weight_adjustments: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    added_dimensions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    partner: Mapped["Partner"] = relationship(back_populates="rubric_overlays")


class Score(Base):
    """One shared base score per company per rubric_base version."""

    __tablename__ = "scores"
    __table_args__ = (
        UniqueConstraint("company_id", "rubric_base_version", name="uq_score_company_base_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    rubric_base_version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    subscores: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    why_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="scores")


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (UniqueConstraint("partner_id", "company_id", name="uq_feedback_partner_company"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id"), nullable=False, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    thumbs: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 or -1
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    partner: Mapped["Partner"] = relationship(back_populates="feedback")
    company: Mapped["Company"] = relationship(back_populates="feedback")
