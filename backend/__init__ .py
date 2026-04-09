# =============================================================================
#  FILE : backend/__init__.py
#  PHASE: 10 — Load Celery when Django starts
#
#  This makes sure Celery is always loaded when Django starts,
#  so the @shared_task decorator works correctly in tasks.py
# =============================================================================

from .celery import app as celery_app

__all__ = ("celery_app",)
