from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

from app.core.config import get_settings, get_thresholds
from app.models.entities import Company, Person


def should_auto_push(base_score: float) -> bool:
    cfg = (get_thresholds().get("auto_push") or {})
    if not cfg.get("enabled", True):
        return False
    return base_score >= float(cfg.get("min_base_score", 70))


async def push_company(
    db: Session,
    *,
    company: Company,
    why_note: str,
    relevant_partner_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Affinity API v2 push. Dry-runs when AFFINITY_API_KEY is unset.
    Creates/updates Organization + attaches note; tags relevant partners when possible.
    """
    settings = get_settings()
    people = db.query(Person).filter(Person.company_id == company.id).all()
    relevant_partner_names = relevant_partner_names or []

    payload = {
        "organization": {
            "name": company.name,
            "domain": company.domain,
            "affinity_org_id": company.affinity_org_id,
        },
        "people": [
            {"name": p.name, "email": p.email, "title": p.title, "affinity_person_id": p.affinity_person_id}
            for p in people
        ],
        "note": why_note,
        "relevant_partners": relevant_partner_names,
    }

    if not settings.affinity_api_key:
        return {"status": "dry_run", "reason": "AFFINITY_API_KEY not set", "payload": payload}

    auth = (settings.affinity_api_key, "")
    base = settings.affinity_base_url.rstrip("/")

    async with httpx.AsyncClient(timeout=30.0, auth=auth) as client:
        org_id = company.affinity_org_id
        if org_id is None:
            # Affinity v1-style orgs endpoint is widely used; v2 paths vary by tenant.
            resp = await client.post(
                f"{base}/organizations",
                json={"name": company.name, "domain": company.domain},
            )
            if resp.status_code >= 400:
                # Try organizations list match by name
                return {
                    "status": "error",
                    "http_status": resp.status_code,
                    "body": resp.text[:1000],
                    "payload": payload,
                }
            data = resp.json()
            org_id = data.get("id") or data.get("organization", {}).get("id")
            if org_id:
                company.affinity_org_id = int(org_id)
                db.add(company)
                db.commit()

        if why_note and org_id:
            await client.post(
                f"{base}/notes",
                json={
                    "organization_ids": [org_id],
                    "content": why_note
                    + (
                        f"\n\nMost relevant partners: {', '.join(relevant_partner_names)}"
                        if relevant_partner_names
                        else ""
                    ),
                },
            )

    return {"status": "pushed", "affinity_org_id": company.affinity_org_id, "payload": payload}
