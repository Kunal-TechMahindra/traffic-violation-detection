# =============================================================================
#  Traffic Violation Detection System
#  FILE : backend/celery.py
#  PHASE: 10 — Celery Configuration
#
#  WHAT THIS FILE DOES:
#    - Sets up Celery to work with Django
#    - Connects Celery to Redis as the message broker
#    - Auto-discovers tasks from all Django apps
#
#  HOW IT WORKS:
#    User uploads video → API saves file → Celery worker picks up the task
#    → runs full pipeline.py in background → saves violations to DB
#    → user can check results anytime via GET /api/violations/
# =============================================================================

import os
from celery import Celery

# Tell Celery which Django settings to use
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

# Create the Celery app
app = Celery("traffic_violation_system")

# Load config from Django settings — any key starting with CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.broker_url = "redis://localhost:6379/0"
app.conf.result_backend = "redis://localhost:6379/0"

# Auto-discover tasks.py in all installed apps
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """Simple test task — run to verify Celery is working."""
    print(f"[CELERY] Debug task running! Request: {self.request!r}")
    return "Celery is working!"
