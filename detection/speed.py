# =============================================================================
#  Traffic Violation Detection System
#  FILE : detection/speed.py
#  PHASE: 4 — Speed Detection
#
#  WHAT THIS FILE DOES:
#    - Draws two virtual lines across the road (Line A and Line B)
#    - Records the frame number when each vehicle crosses Line A
#    - Records the frame number when the same vehicle crosses Line B
#    - Calculates: Time = (Frame_B - Frame_A) / FPS
#    - Calculates: Speed = Real_Distance / Time * 3.6  (converts to km/h)
#    - Flags vehicles exceeding the speed limit as VIOLATIONS
#    - Saves all speed results to a CSV file
#
#  HOW TO RUN:
#    python detection/speed.py
#
#  IMPORTANT — CALIBRATION:
#    You must set LINE_Y1 and LINE_Y2 based on YOUR video.
#    Run the script once with CALIBRATION_MODE = True to find the right values.
# =============================================================================

import cv2
import csv
import os
from datetime import datetime
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort

# -----------------------------------------------------------------------------
# CONFIGURATION — ⚠️ ADJUST THESE FOR YOUR VIDEO
# -----------------------------------------------------------------------------

VIDEO_SOURCE  = "test_data/videos/traffic.mp4"
OUTPUT_VIDEO  = "test_data/videos/output_phase4.mp4"
OUTPUT_CSV    = "logs/speed_results.csv"
MODEL_NAME    = "yolov8n.pt"
CONFIDENCE    = 0.15

# ── Speed detection lines (Y pixel positions in your video) ──────────────────
#
#  Your video is 1920px tall (portrait/vertical video).
#  Line A = upper line (vehicle crosses this first)
#  Line B = lower line (vehicle crosses this second)
#
#  For a 1920px tall video, good starting values:
LINE_Y1 = 1350   # Line A — bottom (vehicles cross FIRST)
LINE_Y2 = 550    # Line B — top    (vehicles cross SECOND)

# ── Real-world distance between the two lines ────────────────────────────────
#  Estimate how many metres apart the two lines are in the real world.
REAL_DISTANCE_METERS = 8.0

# ── Speed limit ───────────────────────────────────────────────────────────────
SPEED_LIMIT_KMPH = 80

# ── Set True to show line positions before running full detection ─────────────
CALIBRATION_MODE = False

# YOLO + Tracker settings
VEHICLE_CLASSES = [2, 3, 5, 7]
CLASS_NAMES     = {2: "Car", 3: "Motorcycle", 5: "Bus", 7: "Truck"}

# -----------------------------------------------------------------------------
# SpeedDetector CLASS
# -----------------------------------------------------------------------------

class SpeedDetector:
    """
    Detects, tracks, and calculates the speed of vehicles
    using two virtual trip lines drawn across the road.
    """

    def __init__(self, fps):
        self.fps          = fps
        self.model        = YOLO(MODEL_NAME)
        self.tracker      = DeepSort(
            max_age=30, n_init=2,
            nms_max_overlap=1.0,
            max_cosine_distance=0.3,
        )

        # Tracking data per vehicle
        # {track_id: {'frame_A': int, 'frame_B': int, 'speed': float, 'class': str}}
        self.vehicle_data = {}

        print(f"[INFO] FPS                   : {fps}")
        print(f"[INFO] Line A (upper) Y pos  : {LINE_Y1} px")
        print(f"[INFO] Line B (lower) Y pos  : {LINE_Y2} px")
        print(f"[INFO] Real distance         : {REAL_DISTANCE_METERS} m")
        print(f"[INFO] Speed limit           : {SPEED_LIMIT_KMPH} km/h\n")

    def update(self, frame, frame_num):
        """
        Process one frame: detect → track → check line crossings → calc speed.

        Returns:
            tracks     : list of active track dicts
            violations : list of violation dicts detected THIS frame
        """

        # ── YOLOv8 detection ──────────────────────────────────────────────────
        results = self.model(frame, conf=CONFIDENCE,
                             classes=VEHICLE_CLASSES, verbose=False)

        raw_detections = []
        for result in results:
            for box in result.boxes:
                cid = int(box.cls[0])
                if cid not in VEHICLE_CLASSES:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                raw_detections.append(
                    ([x1, y1, x2 - x1, y2 - y1], float(box.conf[0]), cid)
                )

        # ── DeepSORT update ───────────────────────────────────────────────────
        updated_tracks = self.tracker.update_tracks(raw_detections, frame=frame)

        tracks     = []
        violations = []

        for track in updated_tracks:
            if not track.is_confirmed():
                continue

            tid  = str(track.track_id)
            ltrb = track.to_ltrb()
            x1, y1, x2, y2 = map(int, ltrb)
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2

            cid        = track.get_det_class()
            class_name = CLASS_NAMES.get(cid, "Vehicle") if cid else "Vehicle"

            # Initialise record for new vehicle
            if tid not in self.vehicle_data:
                self.vehicle_data[tid] = {
                    "frame_A"   : None,
                    "frame_B"   : None,
                    "speed"     : None,
                    "class"     : class_name,
                    "violation" : False,
                    "plate"     : "—",          # filled in Phase 6
                }

            rec = self.vehicle_data[tid]

            # ── Line crossing detection ───────────────────────────────────────
            # Use a ±15px tolerance band around each line
            TOLERANCE = 15

            # Line A crossing — vehicle center passes below LINE_Y1
            if rec["frame_A"] is None:
                if cy >= LINE_Y2 and cy <= LINE_Y1:
                    rec["frame_A"] = frame_num

            # Line B crossing — vehicle moves up past LINE_Y2
            if rec["frame_A"] is not None and rec["frame_B"] is None:
                if cy <= LINE_Y2:
                    rec["frame_B"] = frame_num

            # ── Speed calculation (once both lines crossed) ───────────────────
            if (rec["frame_A"] is not None and
                rec["frame_B"] is not None and
                rec["speed"] is None):

                frames_elapsed = int(rec["frame_B"]) - int(rec["frame_A"])

                if frames_elapsed <= 0:
                    rec["frame_A"] = None
                    rec["frame_B"] = None

                # Ignore if vehicle crossed both lines in under 5 frames
                # (tracking glitch — not a real measurement)
                elif frames_elapsed < 5:
                    rec["frame_A"] = None   # reset and wait for real crossing
                    rec["frame_B"] = None

                else:
                    time_seconds = frames_elapsed / self.fps
                    speed_ms     = REAL_DISTANCE_METERS / time_seconds
                    speed_kmph   = speed_ms * 3.6

                    # ── Glitch filters ────────────────────────────────────────
                    # Too slow  → tracking glitch (vehicle barely moved)
                    if speed_kmph < 20:
                        rec["frame_A"] = None
                        rec["frame_B"] = None

                    # Too fast → tracking glitch (impossible speed)
                    elif speed_kmph > 180:
                        rec["frame_A"] = None
                        rec["frame_B"] = None

                    # ── Valid speed — save and check violation ────────────────
                    else:
                        rec["speed"] = round(speed_kmph, 1)

                        # ✅ FIX: Check violation and flag it
                        if speed_kmph > SPEED_LIMIT_KMPH:
                            rec["violation"] = True
                            violations.append({
                                "track_id"  : tid,
                                "class_name": class_name,
                                "speed"     : rec["speed"],
                                "frame"     : frame_num,
                                "bbox"      : [x1, y1, x2, y2],
                                "timestamp" : datetime.now().strftime("%H:%M:%S"),
                            })
                            print(f"\n  🚨 VIOLATION!  {class_name} #{tid}  →  "
                                  f"{rec['speed']} km/h  "
                                  f"(limit: {SPEED_LIMIT_KMPH} km/h)\n")
                        else:
                            print(f"  ✅ {class_name} #{tid}  →  "
                                  f"{rec['speed']} km/h  (OK)")
            tracks.append({
                "track_id"  : tid,
                "class_name": class_name,
                "bbox"      : [x1, y1, x2, y2],
                "center"    : (cx, cy),
                "speed"     : rec["speed"],
                "violation" : rec["violation"],
            })

        return tracks, violations

    def draw(self, frame, tracks, frame_num):
        """Draw lines, boxes, speed labels, and violation alerts."""
        h, w = frame.shape[:2]

        # ── Draw Line A ───────────────────────────────────────────────────────
        cv2.line(frame, (0, LINE_Y1), (w, LINE_Y1), (0, 255, 255), 2)
        cv2.putText(frame, "Line A", (10, LINE_Y1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        # ── Draw Line B ───────────────────────────────────────────────────────
        cv2.line(frame, (0, LINE_Y2), (w, LINE_Y2), (0, 165, 255), 2)
        cv2.putText(frame, "Line B", (10, LINE_Y2 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

        # ── Draw each vehicle ─────────────────────────────────────────────────
        for t in tracks:
            x1, y1, x2, y2 = t["bbox"]
            tid             = t["track_id"]
            speed           = t["speed"]
            violation       = t["violation"]

            # Box color: red for violation, green for ok, white for unknown
            if violation:
                color = (0, 0, 255)       # Red
            elif speed is not None:
                color = (0, 255, 0)       # Green
            else:
                color = (200, 200, 200)   # Gray (speed not yet calculated)

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Label
            if speed is not None:
                label = f"{t['class_name']} #{tid}  {speed} km/h"
                if violation:
                    label += "  VIOLATION!"
            else:
                label = f"{t['class_name']} #{tid}"

            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(frame, (x1, y1 - th - 10), (x1 + tw + 8, y1), color, -1)
            cv2.putText(frame, label, (x1 + 4, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

        # ── Stats overlay ─────────────────────────────────────────────────────
        violations_total = sum(
            1 for v in self.vehicle_data.values() if v["violation"]
        )
        speeds_calculated = sum(
            1 for v in self.vehicle_data.values() if v["speed"] is not None
        )

        cv2.putText(frame,
                    f"Frame: {frame_num}  |  Speeds: {speeds_calculated}  |  "
                    f"Violations: {violations_total}",
                    (15, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        return frame

    def save_csv(self, output_path):
        """Save all vehicle speed results to CSV."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "track_id", "class", "speed_kmph",
                "violation", "frame_A", "frame_B"
            ])
            for tid, rec in self.vehicle_data.items():
                if rec["speed"] is not None:
                    writer.writerow([
                        tid, rec["class"], rec["speed"],
                        rec["violation"], rec["frame_A"], rec["frame_B"]
                    ])
        print(f"[SAVED] Speed results → {output_path}")


# -----------------------------------------------------------------------------
# CALIBRATION MODE — shows line positions on first frame only
# -----------------------------------------------------------------------------

def run_calibration():
    """Show the first frame with Line A and Line B drawn — adjust Y values."""
    cap = cv2.VideoCapture(VIDEO_SOURCE)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        print("[ERROR] Cannot open video for calibration")
        return

    h, w = frame.shape[:2]
    cv2.line(frame, (0, LINE_Y1), (w, LINE_Y1), (0, 255, 255), 3)
    cv2.putText(frame, f"Line A  Y={LINE_Y1}", (20, LINE_Y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

    cv2.line(frame, (0, LINE_Y2), (w, LINE_Y2), (0, 165, 255), 3)
    cv2.putText(frame, f"Line B  Y={LINE_Y2}", (20, LINE_Y2 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 165, 255), 2)

    print(f"[CALIBRATION] Video size : {w} x {h}")
    print(f"[CALIBRATION] Line A Y   : {LINE_Y1}")
    print(f"[CALIBRATION] Line B Y   : {LINE_Y2}")
    print("[CALIBRATION] Adjust LINE_Y1 and LINE_Y2 so both lines cross the road")
    print("[CALIBRATION] Press any key to close\n")

    cv2.imshow("Calibration — adjust LINE_Y1 and LINE_Y2", frame)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


# -----------------------------------------------------------------------------
# RUN SPEED DETECTION ON VIDEO
# -----------------------------------------------------------------------------

def run_speed_detection():

    if CALIBRATION_MODE:
        run_calibration()
        return

    cap = cv2.VideoCapture(VIDEO_SOURCE)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open: {VIDEO_SOURCE}")
        return

    fps    = cap.get(cv2.CAP_PROP_FPS) or 30
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    detector = SpeedDetector(fps)

    os.makedirs(os.path.dirname(OUTPUT_VIDEO), exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, fps, (width, height))

    print(f"[INFO] Video     : {VIDEO_SOURCE}")
    print(f"[INFO] Output    : {OUTPUT_VIDEO}")
    print("[INFO] Press Q to quit\n")

    frame_num        = 0
    all_violations   = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_num += 1
        tracks, violations = detector.update(frame, frame_num)
        all_violations.extend(violations)

        annotated = detector.draw(frame.copy(), tracks, frame_num)
        writer.write(annotated)
        cv2.imshow("Phase 4 — Speed Detection (Press Q to quit)", annotated)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("\n[INFO] Stopped by user")
            break

    cap.release()
    writer.release()
    cv2.destroyAllWindows()

    # Save CSV
    detector.save_csv(OUTPUT_CSV)

    # Final summary
    speeds = [v["speed"] for v in detector.vehicle_data.values() if v["speed"]]
    viols  = [v for v in detector.vehicle_data.values() if v["violation"]]

    print(f"\n{'='*55}")
    print(f"  Phase 4 — Speed Detection Results")
    print(f"{'='*55}")
    print(f"  Total vehicles tracked   : {len(detector.vehicle_data)}")
    print(f"  Speeds calculated        : {len(speeds)}")
    print(f"  Violations (>{SPEED_LIMIT_KMPH} km/h)    : {len(viols)}")
    if speeds:
        print(f"  Highest speed seen       : {max(speeds)} km/h")
        print(f"  Average speed            : {sum(speeds)/len(speeds):.1f} km/h")
    print(f"  CSV saved to             : {OUTPUT_CSV}")
    print(f"  Video saved to           : {OUTPUT_VIDEO}")
    print(f"\n✅  Phase 4 complete — ready for Phase 5 (License Plate Detection)\n")


# -----------------------------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    run_speed_detection()
