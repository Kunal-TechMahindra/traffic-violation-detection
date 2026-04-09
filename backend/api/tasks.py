# =============================================================================
#  Traffic Violation Detection System
#  FILE : backend/api/tasks.py
#  PHASE: 10 — Celery Async Tasks
#
#  WHAT THIS FILE DOES:
#    - Defines background tasks that Celery workers run
#    - Task 1: process_video_task  → runs full violation pipeline on a video
#    - Task 2: save_violation_task → saves one violation record to database
#    - Task 3: cleanup_old_task    → deletes old processed videos to save space
#
#  HOW TO START THE WORKER (in a new terminal):
#    celery -A backend worker --loglevel=info --pool=solo
#
#  NOTE: --pool=solo is required on Windows
# =============================================================================

import os
import sys
import json
import traceback
from datetime import datetime, timedelta
from celery import shared_task
from django.utils import timezone


# =============================================================================
# TASK 1 — Process a video file through the full detection pipeline
# =============================================================================

@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def process_video_task(self, video_path, job_id=None, speed_limit=80):
    """
    Main background task — runs the full violation detection pipeline
    on an uploaded video file.

    Args:
        video_path  : absolute path to the video file
        job_id      : optional job identifier for tracking
        speed_limit : speed limit in km/h (default 80)

    Returns:
        dict with results summary
    """

    print(f"\n[CELERY] Starting video processing task")
    print(f"[CELERY] Job ID    : {job_id}")
    print(f"[CELERY] Video     : {video_path}")
    print(f"[CELERY] Speed Limit: {speed_limit} km/h\n")

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    try:
        # Update job status to "processing"
        _update_job_status(job_id, "processing", 0)

        # ── Import pipeline modules ───────────────────────────────────────────
        # Add project root to path so detection modules can be found
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        import cv2
        from ultralytics import YOLO
        from deep_sort_realtime.deepsort_tracker import DeepSort
        import re

        # ── Configuration (same as pipeline.py) ──────────────────────────────
        LINE_Y1              = 1350
        LINE_Y2              = 550
        REAL_DISTANCE_METERS = 8.0
        CONFIDENCE           = 0.15
        VEHICLE_CLASSES      = [2, 3, 5, 7]
        CLASS_NAMES          = {2: "Car", 3: "Motorcycle", 5: "Bus", 7: "Truck"}
        VIOLATIONS_DIR       = "media/violations"
        MIN_FRAMES           = 5
        os.makedirs(VIOLATIONS_DIR, exist_ok=True)

        # ── Load models ───────────────────────────────────────────────────────
        print("[CELERY] Loading YOLOv8 model...")
        model   = YOLO("yolov8n.pt")
        tracker = DeepSort(max_age=30, n_init=2,
                           nms_max_overlap=1.0, max_cosine_distance=0.3)

        # ── Load OCR ──────────────────────────────────────────────────────────
        ocr_reader = None
        try:
            import easyocr
            os.environ["OMP_NUM_THREADS"] = "1"
            ocr_reader = easyocr.Reader(
                ['en'], gpu=False, verbose=False, detect_network="dbnet18"
            )
            print("[CELERY] EasyOCR loaded")
        except Exception:
            print("[CELERY] EasyOCR not available — plates will show as UNKNOWN")

        # ── Open video ────────────────────────────────────────────────────────
        cap   = cv2.VideoCapture(video_path)
        fps   = cap.get(cv2.CAP_PROP_FPS) or 30
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        print(f"[CELERY] Video FPS: {fps:.1f}  Total frames: {total}")

        vehicle_data = {}
        violations   = []
        plate_cache  = {}
        frame_num    = 0

        # ── Frame loop ────────────────────────────────────────────────────────
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_num += 1

            # Update progress every 30 frames
            if frame_num % 30 == 0:
                pct = int((frame_num / total) * 100)
                _update_job_status(job_id, "processing", pct)
                print(f"[CELERY] Progress: {frame_num}/{total} ({pct}%)")

            # YOLO detection
            results  = model(frame, conf=CONFIDENCE,
                             classes=VEHICLE_CLASSES, verbose=False)
            raw_dets = []
            for result in results:
                for box in result.boxes:
                    cid = int(box.cls[0])
                    if cid not in VEHICLE_CLASSES:
                        continue
                    x1,y1,x2,y2 = map(int, box.xyxy[0])
                    raw_dets.append(
                        ([x1,y1,x2-x1,y2-y1], float(box.conf[0]), cid)
                    )

            # Tracking
            tracks = tracker.update_tracks(raw_dets, frame=frame)

            for track in tracks:
                if not track.is_confirmed():
                    continue

                tid   = str(track.track_id)
                ltrb  = track.to_ltrb()
                x1,y1,x2,y2 = map(int, ltrb)
                cx, cy = (x1+x2)//2, (y1+y2)//2
                cid   = track.get_det_class()
                cname = CLASS_NAMES.get(cid, "Vehicle") if cid else "Vehicle"

                if tid not in vehicle_data:
                    vehicle_data[tid] = {
                        "frame_A": None, "frame_B": None,
                        "speed": None,   "violation": False,
                        "plate": "",     "class": cname,
                    }

                rec = vehicle_data[tid]

                # Line crossing
                if rec["frame_A"] is None and LINE_Y2 <= cy <= LINE_Y1:
                    rec["frame_A"] = frame_num
                if rec["frame_A"] and not rec["frame_B"] and cy <= LINE_Y2:
                    rec["frame_B"] = frame_num

                # Speed calculation
                if rec["frame_A"] and rec["frame_B"] and rec["speed"] is None:
                    elapsed = int(rec["frame_B"]) - int(rec["frame_A"])
                    if elapsed >= MIN_FRAMES:
                        spd = (REAL_DISTANCE_METERS / (elapsed / fps)) * 3.6
                        if spd <= 200:
                            rec["speed"] = round(spd, 1)

                            if spd > speed_limit:
                                rec["violation"] = True

                                # Read plate
                                plate = _read_plate_ocr(
                                    frame, [x1,y1,x2,y2],
                                    tid, plate_cache, ocr_reader
                                )
                                rec["plate"] = plate

                                # Save evidence image
                                img_path = _save_evidence(
                                    frame, [x1,y1,x2,y2], tid, spd, plate,
                                    VIOLATIONS_DIR
                                )

                                violation_record = {
                                    "track_id"   : tid,
                                    "class_name" : cname,
                                    "speed"      : rec["speed"],
                                    "plate"      : plate or "UNKNOWN",
                                    "frame"      : frame_num,
                                    "image_path" : img_path,
                                    "timestamp"  : datetime.now().isoformat(),
                                    "video_source": os.path.basename(video_path),
                                }
                                violations.append(violation_record)

                                # Save to database immediately
                                save_violation_task.delay(violation_record)

                                print(f"[CELERY] VIOLATION! {cname} #{tid} "
                                      f"→ {spd:.1f} km/h  Plate: {plate or 'UNKNOWN'}")
                    else:
                        rec["frame_A"] = None
                        rec["frame_B"] = None

        cap.release()

        # Final result
        speeds = [v["speed"] for v in vehicle_data.values() if v["speed"]]
        result = {
            "status"            : "completed",
            "job_id"            : job_id,
            "video_path"        : video_path,
            "total_frames"      : frame_num,
            "total_vehicles"    : len(vehicle_data),
            "speeds_calculated" : len(speeds),
            "violations_found"  : len(violations),
            "highest_speed"     : max(speeds) if speeds else 0,
            "average_speed"     : round(sum(speeds)/len(speeds), 1) if speeds else 0,
            "violations"        : violations,
        }

        _update_job_status(job_id, "completed", 100, result)
        print(f"\n[CELERY] Task complete!")
        print(f"[CELERY] Violations found: {len(violations)}")
        return result

    except Exception as exc:
        print(f"\n[CELERY] Task FAILED: {exc}")
        traceback.print_exc()
        _update_job_status(job_id, "failed", 0, {"error": str(exc)})
        raise self.retry(exc=exc)


# =============================================================================
# TASK 2 — Save a single violation to the database
# =============================================================================

@shared_task
def save_violation_task(violation_data):
    """
    Saves one violation record to the database.
    Called automatically by process_video_task for each violation found.

    Args:
        violation_data : dict with track_id, class_name, speed, plate,
                         frame, image_path, timestamp, video_source
    """
    try:
        from backend.api.models import Vehicle, Violation

        # Get or create vehicle record
        vehicle, created = Vehicle.objects.get_or_create(
            track_id=str(violation_data.get("track_id", "0")),
            defaults={
                "vehicle_type": violation_data.get("class_name", "Vehicle")
            }
        )

        # Create violation record
        violation = Violation.objects.create(
            vehicle      = vehicle,
            plate        = violation_data.get("plate", "UNKNOWN"),
            speed        = float(violation_data.get("speed", 0)),
            speed_limit  = 80,
            frame_number = int(violation_data.get("frame", 0)),
            video_source = violation_data.get("video_source", "unknown"),
        )

        # Attach evidence image if it exists
        img_path = violation_data.get("image_path", "")
        if img_path and os.path.exists(img_path):
            from django.core.files import File
            with open(img_path, "rb") as f:
                violation.image.save(
                    os.path.basename(img_path),
                    File(f),
                    save=True
                )

        print(f"[CELERY] Saved violation #{violation.id} — "
              f"Plate: {violation.plate}  Speed: {violation.speed} km/h")
        return {"saved": True, "violation_id": violation.id}

    except Exception as e:
        print(f"[CELERY] Failed to save violation: {e}")
        return {"saved": False, "error": str(e)}


# =============================================================================
# TASK 3 — Cleanup old uploaded videos to save disk space
# =============================================================================

@shared_task
def cleanup_old_videos_task(days_old=7):
    """
    Deletes uploaded video files older than `days_old` days.
    Run this on a schedule to keep disk space under control.

    Args:
        days_old : delete files older than this many days (default 7)
    """
    upload_dir  = "media/uploads"
    cutoff_time = datetime.now() - timedelta(days=days_old)
    deleted     = []
    errors      = []

    if not os.path.exists(upload_dir):
        return {"deleted": 0, "message": "Upload directory not found"}

    for filename in os.listdir(upload_dir):
        if not filename.endswith((".mp4", ".avi", ".mov", ".mkv")):
            continue

        filepath = os.path.join(upload_dir, filename)
        file_time = datetime.fromtimestamp(os.path.getmtime(filepath))

        if file_time < cutoff_time:
            try:
                os.remove(filepath)
                deleted.append(filename)
                print(f"[CELERY] Deleted old video: {filename}")
            except Exception as e:
                errors.append(str(e))

    print(f"[CELERY] Cleanup complete — deleted {len(deleted)} files")
    return {
        "deleted_count" : len(deleted),
        "deleted_files" : deleted,
        "errors"        : errors,
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _update_job_status(job_id, status, progress, result=None):
    """Store job status in a simple JSON file for polling."""
    if not job_id:
        return
    status_dir  = "logs/jobs"
    os.makedirs(status_dir, exist_ok=True)
    status_file = os.path.join(status_dir, f"{job_id}.json")
    data = {
        "job_id"    : job_id,
        "status"    : status,       # queued / processing / completed / failed
        "progress"  : progress,     # 0-100
        "updated_at": datetime.now().isoformat(),
        "result"    : result,
    }
    with open(status_file, "w") as f:
        json.dump(data, f, indent=2)


def _read_plate_ocr(frame, bbox, tid, cache, ocr_reader):
    """Crop plate region and read text with OCR."""
    if tid in cache and cache[tid]:
        return cache[tid]

    import re
    import cv2

    x1, y1, x2, y2 = bbox
    h    = y2 - y1
    py1  = max(0, int(y2 - h * 0.35))
    crop = frame[py1:y2, max(0,x1):min(frame.shape[1],x2)]

    if crop.shape[0] < 10 or crop.shape[1] < 20:
        return ""

    try:
        gray      = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        gray      = cv2.resize(gray, (gray.shape[1]*3, gray.shape[0]*3),
                               interpolation=cv2.INTER_CUBIC)
        gray      = cv2.fastNlMeansDenoising(gray, h=10)
        processed = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        if ocr_reader:
            results = ocr_reader.readtext(
                cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
            )
            texts   = [t for (_, t, c) in results if c >= 0.2]
            raw     = " ".join(texts)
        else:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = (
                r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            )
            raw = pytesseract.image_to_string(
                processed,
                config="--psm 8 --oem 3 -c "
                       "tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            )

        cleaned = re.sub(r"[^A-Z0-9 ]", "", raw.upper()).strip()
        parts   = [p for p in cleaned.split() if len(p) > 1]
        text    = "".join(parts)
        result  = text if len(text) >= 3 else ""
        if result:
            cache[tid] = result
        return result

    except Exception:
        return ""


def _save_evidence(frame, bbox, tid, speed, plate, save_dir):
    """Save cropped vehicle image as evidence."""
    import cv2
    x1, y1, x2, y2 = bbox
    pad  = 20
    crop = frame[max(0,y1-pad):min(frame.shape[0],y2+pad),
                 max(0,x1-pad):min(frame.shape[1],x2+pad)].copy()
    ts   = datetime.now().strftime("%H%M%S")
    name = f"violation_{tid}_{speed}kmh_{plate or 'UNKNOWN'}_{ts}.jpg"
    path = os.path.join(save_dir, name)
    cv2.imwrite(path, crop)
    return path
