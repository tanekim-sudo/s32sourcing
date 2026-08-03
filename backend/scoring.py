"""Base rubric scoring entrypoint."""

from app.services.scoring import rules_score_company, score_company

__all__ = ["score_company", "rules_score_company"]
