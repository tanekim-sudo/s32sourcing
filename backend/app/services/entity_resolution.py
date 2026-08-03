from __future__ import annotations

import re
from typing import Optional

from sqlalchemy.orm import Session

from app.models.entities import Company, Person


def _norm_domain(domain: Optional[str]) -> Optional[str]:
    if not domain:
        return None
    d = domain.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = d.split("/")[0]
    if d.startswith("www."):
        d = d[4:]
    return d or None


def _norm_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    return re.sub(r"\s+", " ", name.strip().lower())


def find_company(
    db: Session,
    *,
    domain: Optional[str] = None,
    name: Optional[str] = None,
    affinity_org_id: Optional[int] = None,
) -> Optional[Company]:
    if affinity_org_id is not None:
        hit = db.query(Company).filter(Company.affinity_org_id == affinity_org_id).one_or_none()
        if hit:
            return hit

    nd = _norm_domain(domain)
    if nd:
        hit = db.query(Company).filter(Company.domain == nd).one_or_none()
        if hit:
            return hit

    nn = _norm_name(name)
    if nn:
        # Exact case-insensitive name match for firm-wide canonical record
        for company in db.query(Company).all():
            if _norm_name(company.name) == nn:
                return company
    return None


def upsert_company(
    db: Session,
    *,
    name: str,
    domain: Optional[str] = None,
    description: Optional[str] = None,
    affinity_org_id: Optional[int] = None,
    raw_payload: Optional[dict] = None,
) -> tuple[Company, bool]:
    """Return (company, created). Never creates a second copy of the same firm entity."""
    existing = find_company(
        db,
        domain=domain,
        name=name,
        affinity_org_id=affinity_org_id,
    )
    if existing:
        changed = False
        if description and not existing.description:
            existing.description = description
            changed = True
        nd = _norm_domain(domain)
        if nd and not existing.domain:
            existing.domain = nd
            changed = True
        if affinity_org_id and not existing.affinity_org_id:
            existing.affinity_org_id = affinity_org_id
            changed = True
        if raw_payload:
            merged = dict(existing.raw_payload or {})
            merged.update(raw_payload)
            existing.raw_payload = merged
            changed = True
        if changed:
            db.add(existing)
            db.flush()
        return existing, False

    company = Company(
        name=name.strip(),
        domain=_norm_domain(domain),
        description=description,
        affinity_org_id=affinity_org_id,
        raw_payload=raw_payload or {},
    )
    db.add(company)
    db.flush()
    return company, True


def upsert_person(
    db: Session,
    *,
    name: str,
    company_id: Optional[int] = None,
    email: Optional[str] = None,
    title: Optional[str] = None,
    linkedin_url: Optional[str] = None,
    affinity_person_id: Optional[int] = None,
    raw_payload: Optional[dict] = None,
) -> tuple[Person, bool]:
    if affinity_person_id is not None:
        hit = db.query(Person).filter(Person.affinity_person_id == affinity_person_id).one_or_none()
        if hit:
            return hit, False
    if linkedin_url:
        hit = db.query(Person).filter(Person.linkedin_url == linkedin_url).one_or_none()
        if hit:
            return hit, False
    if email:
        hit = db.query(Person).filter(Person.email == email.lower()).one_or_none()
        if hit:
            return hit, False

    person = Person(
        name=name.strip(),
        company_id=company_id,
        email=email.lower() if email else None,
        title=title,
        linkedin_url=linkedin_url,
        affinity_person_id=affinity_person_id,
        raw_payload=raw_payload or {},
    )
    db.add(person)
    db.flush()
    return person, True
