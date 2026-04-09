# =============================================================================
#  Traffic Violation Detection System
#  FILE : detection/tracker.py
#  PHASE: 3 — Vehicle Tracking using DeepSORT
#
#  WHAT THIS FILE DOES:
#    - Takes detections from Phase 2 (YOLOv8 bounding boxes)
#    - Assigns a unique ID to each vehicle  e.g. Car #5, Truck #12
#    - Keeps the SAME ID on the SAME vehicle across every frame
#    - Draws colored ID boxes that follow each vehicle through the video
#    - Saves the output as a new annotated tracking video
#
#  HOW TO RUN:
#    python detection/tracker.py
# =============================================================================

import cv2
import random
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
import os

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------

VIDEO_SOURCE  = "test_data/videos/traffic.mp4"
OUTPUT_VIDEO  = "test_data/videos/output_phase3.mp4"
MODEL_NAME    = "yolov8n.pt"
CONFIDENCE    = 0.15

# YOLO vehicle class IDs (COCO dataset)
VEHICLE_CLASSES = [2, 3, 5, 7]
CLASS_NAMES     = {2: "Car", 3: "Motorcycle", 5: "Bus", 7: "Truck"}

# DeepSORT settings
MAX_AGE        = 30   # frames to keep a lost track alive before deleting
MIN_HITS       = 2    # min detections before showing the track
IOU_THRESHOLD  = 0.3  # overlap threshold for matching detections to tracks

# -----------------------------------------------------------------------------
# COLOR GENERATOR  — each vehicle ID gets its own consistent color
# -----------------------------------------------------------------------------

def get_color(track_id):
    """Return a consistent BGR color for a given track ID."""
    random.seed(int(track_id) * 7 + 13)
    r = random.randint(80, 255)
    g = random.randint(80, 255)
    b = random.randint(80, 255)
    return (b, g, r)

# -----------------------------------------------------------------------------
# VehicleTracker CLASS
# -----------------------------------------------------------------------------

class VehicleTracker:
    """
    Wraps YOLOv8 detection + DeepSORT tracking.
    Each vehicle gets a unique integer ID that persists across frames.
    """

    def __init__(self):
        print(f"\n[INFO] Loading YOLOv8 model  : {MODEL_NAME}")
        self.model = YOLO(MODEL_NAME)
        print("[INFO] YOLOv8 loaded!")

        print("[INFO] Initializing DeepSORT tracker...")
        self.tracker = DeepSort(
            max_age=MAX_AGE,
            n_init=MIN_HITS,
            nms_max_overlap=1.0,
            max_cosine_distance=0.3,
            nn_budget=None,
        )
        print("[INFO] DeepSORT ready!")
        print(f"[INFO] Confidence threshold  : {CONFIDENCE}")
        print(f"[INFO] Max track age (frames): {MAX_AGE}\n")

        # Store track history: {track_id: [(cx, cy), ...]}
        self.track_history = {}

    def detect_and_track(self, frame):
        """
        Run YOLOv8 on a frame, then update DeepSORT tracker.

        Returns:
            tracks : list of dicts, each containing:
                {
                  'track_id'  : int   — unique vehicle ID
                  'class_name': str   — 'Car', 'Truck', etc.
                  'bbox'      : [x1, y1, x2, y2]
                  'center'    : (cx, cy)
                }
        """
        # ── Step 1: YOLOv8 detection ─────────────────────────────────────────
        results = self.model(
            frame,
            conf=CONFIDENCE,
            classes=VEHICLE_CLASSES,
            verbose=False
        )

        # ── Step 2: Format detections for DeepSORT ───────────────────────────
        # DeepSORT expects: [([x, y, w, h], confidence, class_id), ...]
        raw_detections = []
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                if class_id not in VEHICLE_CLASSES:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                w    = x2 - x1
                h    = y2 - y1
                raw_detections.append(([x1, y1, w, h], conf, class_id))

        # ── Step 3: Update DeepSORT ───────────────────────────────────────────
        updated_tracks = self.tracker.update_tracks(raw_detections, frame=frame)

        # ── Step 4: Collect confirmed tracks ─────────────────────────────────
        active_tracks = []
        for track in updated_tracks:
            if not track.is_confirmed():
                continue

            track_id = track.track_id
            ltrb     = track.to_ltrb()              # [x1, y1, x2, y2]
            x1, y1, x2, y2 = map(int, ltrb)
            cx, cy   = (x1 + x2) // 2, (y1 + y2) // 2

            # Get class name
            class_id   = track.get_det_class()
            class_name = CLASS_NAMES.get(class_id, "Vehicle") if class_id is not None else "Vehicle"

            # Store center history for trail drawing
            if track_id not in self.track_history:
                self.track_history[track_id] = []
            self.track_history[track_id].append((cx, cy))
            if len(self.track_history[track_id]) > 40:  # keep last 40 points
                self.track_history[track_id].pop(0)

            active_tracks.append({
                "track_id"  : track_id,
                "class_name": class_name,
                "bbox"      : [x1, y1, x2, y2],
                "center"    : (cx, cy),
            })

        return active_tracks

    def draw(self, frame, tracks):
        """
        Draw tracking boxes, IDs, and movement trails on a frame.
        """
        for t in tracks:
            tid    = t["track_id"]
            label  = f"{t['class_name']} #{tid}"
            x1, y1, x2, y2 = t["bbox"]
            cx, cy = t["center"]
            color  = get_color(tid)

            # ── Bounding box ──────────────────────────────────────────────────
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # ── Label background ──────────────────────────────────────────────
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(frame, (x1, y1 - th - 10), (x1 + tw + 8, y1), color, -1)
            cv2.putText(frame, label, (x1 + 4, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # ── Center dot ────────────────────────────────────────────────────
            cv2.circle(frame, (cx, cy), 4, color, -1)

            # ── Movement trail ────────────────────────────────────────────────
            history = self.track_history.get(tid, [])
            for i in range(1, len(history)):
                alpha = int(200 * i / len(history))   # fade older points
                cv2.line(frame, history[i - 1], history[i], color, 1)

        # ── Stats overlay ─────────────────────────────────────────────────────
        total_tracks = len(self.track_history)
        active       = len(tracks)
        cv2.putText(frame, f"Active: {active}  |  Total seen: {total_tracks}",
                    (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)

        return frame


# -----------------------------------------------------------------------------
# RUN TRACKING ON VIDEO
# -----------------------------------------------------------------------------

def run_tracking(video_source=VIDEO_SOURCE, output_path=OUTPUT_VIDEO):
    """
    Open a video, run detection + tracking on every frame,
    show live preview, and save annotated output video.
    """

    tracker = VehicleTracker()

    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video: {video_source}")
        return

    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS) or 30
    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"[INFO] Video     : {video_source}")
    print(f"[INFO] Resolution: {width} x {height}")
    print(f"[INFO] FPS       : {fps:.1f}")
    print(f"[INFO] Frames    : {total}")
    print(f"[INFO] Output    : {output_path}")
    print("[INFO] Press Q to quit\n")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_num    = 0
    all_track_ids = set()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_num += 1
        tracks    = tracker.detect_and_track(frame)
        annotated = tracker.draw(frame.copy(), tracks)

        # Collect all unique IDs seen so far
        for t in tracks:
            all_track_ids.add(t["track_id"])

        # Frame info overlay
        cv2.putText(annotated, f"Frame: {frame_num}/{total}",
                    (15, height - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        writer.write(annotated)
        cv2.imshow("Phase 3 — Vehicle Tracking (Press Q to quit)", annotated)

        # Print progress every 30 frames
        if frame_num % 30 == 0 or frame_num == 1:
            ids = [t['track_id'] for t in tracks]
            print(f"  Frame {frame_num:>5}/{total}  |  "
                  f"Active tracks: {len(tracks)}  |  "
                  f"IDs active: {ids}")

        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("\n[INFO] Stopped by user (Q pressed)")
            break

    cap.release()
    writer.release()
    cv2.destroyAllWindows()

    print(f"\n[DONE] Tracking complete!")
    print(f"[DONE] Total unique vehicles tracked : {len(all_track_ids)}")
    print(f"[DONE] Output saved to               : {output_path}")
    print("\n✅  Phase 3 complete — ready for Phase 4 (Speed Detection)\n")


# -----------------------------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    run_tracking()
