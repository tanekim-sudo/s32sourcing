"""Shim so overlay scoring is importable as backend/overlay_scoring.py per repo plan."""

from app.services.overlay_scoring import apply_overlay

__all__ = ["apply_overlay"]
