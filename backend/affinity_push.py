"""Affinity push entrypoint."""

from app.services.affinity import push_company, should_auto_push

__all__ = ["should_auto_push", "push_company"]
