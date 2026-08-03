from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

import httpx
import yaml
from sqlalchemy.orm import Session

from app.core.config import REPO_ROOT, get_settings
from app.models.entities import Company, RubricBase, Score, Signal


def load_active_rubric(db: Session) -> tuple[str, dict, str]:
    active = (
        db.query(RubricBase)
        .filter(RubricBase.is_active.is_(True))
        .order_by(RubricBase.created_at.desc())
        .first()
    )
    if active:
        data = yaml.safe_load(active.yaml_content) or {}
        return active.version, data, active.yaml_content

    path = REPO_ROOT / "rubric" / "rubric_base.v1.yaml"
    content = path.read_text(encoding="utf-8")
    data = yaml.safe_load(content) or {}
    return str(data.get("version", "1.0.0")), data, content


def _signal_blob(signals: List[Signal]) -> str:
    parts = []
    for s in signals:
        parts.append(
            f"[{s.source}] {s.title or ''}\n{s.summary or ''}\n{json.dumps(s.payload or {}, default=str)[:1500]}"
        )
    return "\n\n".join(parts)


def _keyword_hits(text: str, keywords: List[str]) -> int:
    t = text.lower()
    return sum(1 for k in keywords if k.lower() in t)


def rules_score_company(company: Company, signals: List[Signal], rubric: dict) -> Dict[str, Any]:
    """Hybrid rules pass — works offline without Anthropic."""
    blob = _signal_blob(signals).lower()
    desc = (company.description or "").lower()
    text = f"{company.name} {desc} {blob}"

    dimensions = rubric.get("dimensions") or {}
    subscores: Dict[str, Any] = {}
    evidence: Dict[str, Any] = {}

    heuristics = {
        "founder_quality": {
            "positive": ["founder", "ex-", "alumni", "phd", "former", "repeat founder", "cto", "ceo"],
            "base": 45,
        },
        "market_timing_fit": {
            "positive": ["ai", "llm", "infra", "platform", "regulation", "market", "timing", "category"],
            "base": 40,
        },
        "vc_attention": {
            # High hits = MORE attention = worse for us (negative weight applied later)
            "positive": ["series a", "series b", "raised", "a16z", "sequoia", "funded", "venture"],
            "base": 30,
        },
        "traction_signal": {
            "positive": ["revenue", "arr", "customers", "users", "growth", "stars", "hiring", "mrr"],
            "base": 35,
        },
        "network_proximity": {
            "positive": ["warm", "intro", "affinity", "alumni", "shared", "portfolio"],
            "base": 25,
        },
    }

    for dim_name in dimensions:
        h = heuristics.get(dim_name, {"positive": [], "base": 40})
        hits = _keyword_hits(text, h["positive"])
        score = min(95.0, h["base"] + hits * 8.0)
        # Source diversity bump
        sources = {s.source for s in signals}
        score = min(95.0, score + max(0, len(sources) - 1) * 3)
        cited = [s.title or s.url or s.source for s in signals[:3]]
        subscores[dim_name] = {"score": round(score, 2), "method": "rules"}
        evidence[dim_name] = {
            "keyword_hits": hits,
            "sources": sorted(sources),
            "citations": cited,
        }

    # Weighted total (supports negative weights generically)
    weights = {k: float(v.get("weight", 0)) for k, v in dimensions.items()}
    abs_sum = sum(abs(w) for w in weights.values()) or 1.0
    total = 0.0
    for dim, weight in weights.items():
        value = float(subscores.get(dim, {}).get("score", 0))
        total += value * (weight / abs_sum)

    # Shift negative-capable weighted sum into roughly 0–100 band for UX
    # When negative weights are present, a high vc_attention lowers total.
    total = max(0.0, min(100.0, total))

    return {
        "total_score": round(total, 2),
        "subscores": subscores,
        "evidence": evidence,
        "method": "rules",
    }


async def llm_enrich_score(
    *,
    company: Company,
    signals: List[Signal],
    rubric_yaml: str,
    rules_result: Dict[str, Any],
) -> Dict[str, Any]:
    """Optional Anthropic pass — skipped if ANTHROPIC_API_KEY missing."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        return rules_result

    prompt = f"""You are scoring a startup for a VC firm using this rubric YAML:

{rubric_yaml}

Company: {company.name}
Domain: {company.domain}
Description: {company.description}

Signals:
{_signal_blob(signals)[:8000]}

Rules baseline (JSON):
{json.dumps(rules_result, indent=2)[:4000]}

Return ONLY JSON with keys:
total_score (0-100), subscores (dim -> {{score, rationale}}), evidence (dim -> {{citations: [str]}}).
Respect negative-weight dimensions by scoring the underlying signal high when the undesirable trait is present
(the weight application happens separately — just score the dimension 0-100).
"""

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            if resp.status_code != 200:
                return rules_result
            data = resp.json()
            text = "".join(
                b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
            )
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                return rules_result
            parsed = json.loads(match.group(0))
            parsed["method"] = "hybrid_rules_llm"
            # Keep rules evidence if LLM omitted citations
            if "evidence" not in parsed:
                parsed["evidence"] = rules_result.get("evidence", {})
            return parsed
    except Exception:
        return rules_result


async def score_company(db: Session, company_id: int, *, force: bool = False) -> Optional[Score]:
    company = db.query(Company).filter(Company.id == company_id).one_or_none()
    if not company:
        return None

    version, rubric, yaml_content = load_active_rubric(db)
    existing = (
        db.query(Score)
        .filter(Score.company_id == company_id, Score.rubric_base_version == version)
        .one_or_none()
    )
    if existing and not force:
        return existing

    signals = db.query(Signal).filter(Signal.company_id == company_id).all()
    rules_result = rules_score_company(company, signals, rubric)
    result = await llm_enrich_score(
        company=company,
        signals=signals,
        rubric_yaml=yaml_content,
        rules_result=rules_result,
    )

    from app.services.notes import generate_why_note

    why = generate_why_note(company=company, score=result, signals=signals)

    if existing:
        existing.total_score = float(result["total_score"])
        existing.subscores = result.get("subscores") or {}
        existing.evidence = result.get("evidence") or {}
        existing.why_note = why
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    score = Score(
        company_id=company_id,
        rubric_base_version=version,
        total_score=float(result["total_score"]),
        subscores=result.get("subscores") or {},
        evidence=result.get("evidence") or {},
        why_note=why,
    )
    db.add(score)
    db.commit()
    db.refresh(score)
    return score
