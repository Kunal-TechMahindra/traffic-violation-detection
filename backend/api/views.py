# =============================================================================
#  Traffic Violation Detection System
#  FILE : backend/api/views.py  (UPDATED for Phase 10)
#  PHASE: 10 — Add video upload endpoint that triggers Celery task
#
#  NEW ENDPOINT ADDED:
#    POST /api/process-video/   → upload video → Celery processes it
#    GET  /api/job/{job_id}/    → check processing progress
# =============================================================================

import os
import uuid
import json
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Avg, Max, Min, Count
from django.utils import timezone
from django.conf import settings

from .models import Vehicle, Violation
from .serializers import VehicleSerializer, ViolationSerializer


# ── Existing ViewSets (unchanged from Phase 9) ────────────────────────────────

class ViolationViewSet(viewsets.ModelViewSet):
    queryset         = Violation.objects.all().select_related("vehicle")
    serializer_class = ViolationSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        plate     = self.request.query_params.get("plate")
        min_speed = self.request.query_params.get("min_speed")
        vtype     = self.request.query_params.get("type")
        today     = self.request.query_params.get("today")
        if plate:     qs = qs.filter(plate__icontains=plate)
        if min_speed: qs = qs.filter(speed__gte=float(min_speed))
        if vtype:     qs = qs.filter(vehicle__vehicle_type__icontains=vtype)
        if today:     qs = qs.filter(timestamp__date=timezone.now().date())
        return qs

    from rest_framework.decorators import action

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        qs    = Violation.objects.all()
        total = qs.count()
        if total == 0:
            return Response({
                "total_violations": 0, "average_speed": 0,
                "highest_speed": 0,   "today_violations": 0,
                "unique_plates": 0,   "by_vehicle_type": {},
            })
        agg = qs.aggregate(avg=Avg("speed"), high=Max("speed"), low=Min("speed"))
        return Response({
            "total_violations" : total,
            "average_speed"    : round(agg["avg"] or 0, 1),
            "highest_speed"    : round(agg["high"] or 0, 1),
            "lowest_speed"     : round(agg["low"] or 0, 1),
            "today_violations" : qs.filter(timestamp__date=timezone.now().date()).count(),
            "unique_plates"    : qs.values("plate").distinct().count(),
            "by_vehicle_type"  : {
                i["vehicle__vehicle_type"]: i["count"]
                for i in qs.values("vehicle__vehicle_type").annotate(count=Count("id"))
            },
        })


class VehicleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset         = Vehicle.objects.all().annotate(violation_count=Count("violations"))
    serializer_class = VehicleSerializer


@api_view(["GET"])
def vehicle_by_plate(request, plate):
    violations = Violation.objects.filter(
        plate__icontains=plate).select_related("vehicle")
    if not violations.exists():
        return Response(
            {"detail": f"No violations found for plate: {plate}"},
            status=status.HTTP_404_NOT_FOUND)
    serializer = ViolationSerializer(violations, many=True,
                                     context={"request": request})
    return Response({
        "plate": plate.upper(),
        "total_violations": violations.count(),
        "violations": serializer.data,
    })


@api_view(["POST"])
def upload_violation(request):
    data = request.data
    try:
        vehicle, _ = Vehicle.objects.get_or_create(
            track_id=data.get("track_id", "0"),
            defaults={"vehicle_type": data.get("vehicle_type", "Vehicle")}
        )
        violation = Violation.objects.create(
            vehicle      = vehicle,
            plate        = data.get("plate", "UNKNOWN"),
            speed        = float(data.get("speed", 0)),
            speed_limit  = int(data.get("speed_limit", 80)),
            frame_number = int(data.get("frame_number", 0)),
            video_source = data.get("video_source", "traffic.mp4"),
        )
        if "image" in request.FILES:
            violation.image = request.FILES["image"]
            violation.save()
        serializer = ViolationSerializer(violation, context={"request": request})
        return Response({"status": "saved", "violation": serializer.data},
                        status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ── NEW Phase 10 Endpoints ────────────────────────────────────────────────────

@api_view(["POST"])
def process_video(request):
    """
    POST /api/process-video/

    Upload a video file → save it → trigger Celery background task.

    Request: multipart/form-data with field 'video'
    Optional: speed_limit (int, default 80)

    Response:
    {
        "status"   : "queued",
        "job_id"   : "abc123",
        "message"  : "Video uploaded. Processing started in background.",
        "check_url": "/api/job/abc123/"
    }
    """
    if "video" not in request.FILES:
        return Response(
            {"error": "No video file provided. Send file in 'video' field."},
            status=status.HTTP_400_BAD_REQUEST
        )

    video_file  = request.FILES["video"]
    speed_limit = int(request.data.get("speed_limit", 80))

    # Validate file type
    allowed = [".mp4", ".avi", ".mov", ".mkv"]
    ext     = os.path.splitext(video_file.name)[1].lower()
    if ext not in allowed:
        return Response(
            {"error": f"File type '{ext}' not supported. Use: {allowed}"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Save video to media/uploads/
    upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    job_id     = str(uuid.uuid4())[:8]
    filename   = f"{job_id}_{video_file.name}"
    video_path = os.path.join(upload_dir, filename)

    with open(video_path, "wb") as f:
        for chunk in video_file.chunks():
            f.write(chunk)

    print(f"\n[API] Video saved: {video_path}")
    print(f"[API] Job ID: {job_id}")
    print(f"[API] Sending to Celery worker...\n")

    # Fire Celery task in background (non-blocking!)
    try:
        from backend.api.tasks import process_video_task
        from celery import current_app

        # Force correct broker URL at dispatch time
        current_app.conf.broker_url     = "redis://localhost:6379/0"
        current_app.conf.result_backend = "redis://localhost:6379/0"

        task = process_video_task.apply_async(
            kwargs={
                "video_path"  : video_path,
                "job_id"      : job_id,
                "speed_limit" : speed_limit,
            }
        )
        return Response({
            "status"   : "queued",
            "job_id"   : job_id,
            "task_id"  : str(task.id),
            "filename" : filename,
            "message"  : "Video uploaded. Processing started in background.",
            "check_url": f"/api/job/{job_id}/",
        }, status=status.HTTP_202_ACCEPTED)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({
            "status"  : "error",
            "error"   : str(e),
            "message" : "Task dispatch failed. Check Terminal 1 for full traceback."
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    

@api_view(["GET"])
def check_job_status(request, job_id):
    """
    GET /api/job/{job_id}/

    Check the processing status of an uploaded video.

    Response:
    {
        "job_id"  : "abc123",
        "status"  : "processing",   ← queued / processing / completed / failed
        "progress": 45,             ← 0-100 percent
        "result"  : { ... }         ← filled when completed
    }
    """
    status_file = os.path.join("logs", "jobs", f"{job_id}.json")

    if not os.path.exists(status_file):
        return Response(
            {"error": f"Job '{job_id}' not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        with open(status_file, "r") as f:
            data = json.load(f)
        return Response(data)
    except Exception as e:
        return Response(
            {"error": f"Could not read job status: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
