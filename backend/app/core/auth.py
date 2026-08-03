from __future__ import annotations

from typing import Optional

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.entities import Partner, PartnerRole

_bearer = HTTPBearer(auto_error=False)


async def _verify_clerk_token(token: str) -> dict:
    """Verify Clerk session JWT via Clerk Backend API (robust for scaffold)."""
    settings = get_settings()
    if not settings.clerk_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clerk is not configured",
        )

    # Prefer decode with JWKS when iss is present; fall back to Clerk sessions endpoint.
    try:
        unverified = jwt.decode(token, options={"verify_signature": False})
        issuer = unverified.get("iss")
        if issuer:
            jwks_url = issuer.rstrip("/") + "/.well-known/jwks.json"
            client = PyJWKClient(jwks_url)
            signing_key = client.get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )
    except Exception:
        pass

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://api.clerk.com/v1/clients/verify",
            headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
            params={"token": token},
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Clerk session",
            )
        data = resp.json()
        return {
            "sub": data.get("id") or data.get("user_id"),
            "email": (data.get("email_addresses") or [{}])[0].get("email_address"),
            "name": f"{data.get('first_name') or ''} {data.get('last_name') or ''}".strip(),
        }


def _upsert_partner(
    db: Session,
    *,
    clerk_user_id: Optional[str],
    email: str,
    name: str,
) -> Partner:
    partner = None
    if clerk_user_id:
        partner = db.query(Partner).filter(Partner.clerk_user_id == clerk_user_id).one_or_none()
    if partner is None and email:
        partner = db.query(Partner).filter(Partner.email == email).one_or_none()

    if partner is None:
        partner = Partner(
            name=name or email.split("@")[0],
            email=email,
            clerk_user_id=clerk_user_id,
            role=PartnerRole.partner,
        )
        db.add(partner)
        db.commit()
        db.refresh(partner)
        return partner

    changed = False
    if clerk_user_id and partner.clerk_user_id != clerk_user_id:
        partner.clerk_user_id = clerk_user_id
        changed = True
    if name and partner.name != name:
        partner.name = name
        changed = True
    if changed:
        db.commit()
        db.refresh(partner)
    return partner


async def get_current_partner(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Partner:
    settings = get_settings()

    if settings.auth_dev_bypass:
        return _upsert_partner(
            db,
            clerk_user_id="dev_bypass",
            email=settings.auth_dev_partner_email,
            name="Dev Partner",
        )

    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    claims = await _verify_clerk_token(credentials.credentials)
    clerk_user_id = claims.get("sub")
    email = claims.get("email") or claims.get("primary_email")
    if not email:
        # Clerk session JWTs often put email in nested claims; try common locations
        email = (claims.get("email_addresses") or [None])[0]
    if isinstance(email, dict):
        email = email.get("email_address")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing email")

    name = claims.get("name") or claims.get("full_name") or str(email).split("@")[0]
    return _upsert_partner(db, clerk_user_id=clerk_user_id, email=str(email), name=str(name))


def require_admin(partner: Partner = Depends(get_current_partner)) -> Partner:
    if partner.role != PartnerRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return partner
