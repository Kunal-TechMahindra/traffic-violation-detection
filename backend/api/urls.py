# =============================================================================
#  FILE: backend/api/urls.py  (UPDATED for Phase 10)
#  Add new endpoints: process-video and job status
# =============================================================================

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"violations", views.ViolationViewSet, basename="violation")
router.register(r"vehicles",   views.VehicleViewSet,   basename="vehicle")

urlpatterns = [
    path("",                          include(router.urls)),
    path("vehicle/<str:plate>/",      views.vehicle_by_plate,   name="vehicle-by-plate"),
    path("upload-violation/",         views.upload_violation,    name="upload-violation"),

    # ── Phase 10: Async video processing ─────────────────────────────────────
    path("process-video/",            views.process_video,       name="process-video"),
    path("job/<str:job_id>/",         views.check_job_status,    name="job-status"),
]


# =============================================================================
#  ADD THESE LINES to the bottom of backend/settings.py
#  (do NOT replace settings.py — just add these lines at the end)
# =============================================================================

CELERY_SETTINGS = """

# ── Celery + Redis Configuration (add to bottom of settings.py) ──────────────

CELERY_BROKER_URL        = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND    = "redis://localhost:6379/0"
CELERY_ACCEPT_CONTENT    = ["json"]
CELERY_TASK_SERIALIZER   = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE          = "Asia/Kolkata"

# Optional: auto-delete task results after 1 hour
CELERY_RESULT_EXPIRES    = 3600
"""

print("""
=== INSTRUCTIONS FOR SETTINGS.PY ===
Open backend/settings.py and ADD these lines at the very bottom:

CELERY_BROKER_URL        = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND    = "redis://localhost:6379/0"
CELERY_ACCEPT_CONTENT    = ["json"]
CELERY_TASK_SERIALIZER   = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE          = "Asia/Kolkata"
""") if __name__ == "__main__" else None
