from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


class PartnerOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str

    model_config = {"from_attributes": True}


class QueueCompanyOut(BaseModel):
    company_id: int
    name: str
    domain: Optional[str] = None
    description: Optional[str] = None
    base_score: Optional[float] = None
    overlay_score: Optional[float] = None
    rubric_base_version: Optional[str] = None
    why_note: Optional[str] = None
    matched_thesis_config_ids: List[int] = []
    on_my_watchlist: bool = False


class QueueResponse(BaseModel):
    partner: PartnerOut
    items: List[QueueCompanyOut]
    total: int
    setup_required: bool = False


class HealthOut(BaseModel):
    status: str
    auth_mode: str


class ThesisConfigCreate(BaseModel):
    name: str
    # Partner-facing: plain topics. Server expands into keywords/exa/github.
    topics: List[str] = Field(default_factory=list)
    keywords: List[Any] = Field(default_factory=list)
    exa_queries: List[Any] = Field(default_factory=list)
    github_topics: List[Any] = Field(default_factory=list)
    is_shared: bool = False
    is_active: bool = True
    partner_id: Optional[int] = None  # only admins may set null/shared for others


class ThesisConfigUpdate(BaseModel):
    name: Optional[str] = None
    topics: Optional[List[str]] = None
    keywords: Optional[List[Any]] = None
    exa_queries: Optional[List[Any]] = None
    github_topics: Optional[List[Any]] = None
    is_shared: Optional[bool] = None
    is_active: Optional[bool] = None


class ThesisConfigOut(BaseModel):
    id: int
    partner_id: Optional[int]
    name: str
    keywords: List[Any]
    exa_queries: List[Any]
    github_topics: List[Any]
    is_shared: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class WatchlistCreate(BaseModel):
    company_id: int
    note: Optional[str] = None


class WatchlistEntryOut(BaseModel):
    id: int
    partner_id: int
    company_id: int
    note: Optional[str]
    created_at: datetime
    company_name: Optional[str] = None

    model_config = {"from_attributes": True}


class RubricOverlayUpsert(BaseModel):
    version: str = "1"
    base_rubric_version: str = "1.0.0"
    weight_adjustments: Dict[str, float] = Field(default_factory=dict)
    added_dimensions: List[Any] = Field(default_factory=list)


class RubricOverlayOut(BaseModel):
    id: int
    partner_id: int
    version: str
    base_rubric_version: str
    weight_adjustments: Dict[str, Any]
    added_dimensions: List[Any]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RubricBaseOut(BaseModel):
    id: int
    version: str
    yaml_content: str
    is_active: bool
    changelog: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class RubricBaseCreate(BaseModel):
    version: str
    yaml_content: str
    changelog: Optional[str] = None
    activate: bool = True


class FeedbackCreate(BaseModel):
    thumbs: int  # 1 or -1
    comment: Optional[str] = None


class FeedbackOut(BaseModel):
    id: int
    partner_id: int
    partner_name: Optional[str] = None
    company_id: int
    thumbs: int
    comment: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class SubscoreOut(BaseModel):
    score: float
    rationale: Optional[str] = None
    method: Optional[str] = None


class CompanyDetailOut(BaseModel):
    id: int
    name: str
    domain: Optional[str]
    description: Optional[str]
    affinity_org_id: Optional[int]
    base_score: Optional[float] = None
    overlay_score: Optional[float] = None
    rubric_base_version: Optional[str] = None
    subscores: Dict[str, Any] = Field(default_factory=dict)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    why_note: Optional[str] = None
    partner_lines: List[str] = Field(default_factory=list)
    watchlisted_by: List[str] = Field(default_factory=list)
    signals: List[Dict[str, Any]] = Field(default_factory=list)
    feedback: List[FeedbackOut] = Field(default_factory=list)
    on_my_watchlist: bool = False


class PipelineRunOut(BaseModel):
    report: Dict[str, Any]


class CompanyCreate(BaseModel):
    name: str
    domain: Optional[str] = None
    description: Optional[str] = None
