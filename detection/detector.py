# =============================================================================
#  Traffic Violation Detection System
#  FILE : detection/detector.py
#  PHASE: 2 — Vehicle Detection using YOLOv8
#
#  WHAT THIS FILE DOES:
#    - Loads the YOLOv8 model (downloads automatically on first run ~6 MB)
#    - Reads a video file frame by frame
#    - Detects only vehicles (car, truck, bus, motorcycle) in each frame
#    - Draws bounding boxes + labels + confidence scores on each frame
#    - Saves the output as a new annotated video
#    - Shows a live preview window while processing
#
#  HOW TO RUN:
#    python detection/detector.py
# =============================================================================

import cv2
from ultralytics import YOLO
import os

# -----------------------------------------------------------------------------
# CONFIGURATION  —  change these values as needed
# -----------------------------------------------------------------------------

# Path to your input video. 
# Options:
#   - Put a traffic video in test_data/videos/ and set the path below
#   - Use 0 for your webcam (live camera)
VIDEO_SOURCE = "test_data/videos/traffic.mp4"   # ← change to your video file
# VIDEO_SOURCE = 0                               # ← uncomment for webcam

# Where to save the output annotated video
OUTPUT_VIDEO = "test_data/videos/output_phase2.mp4"

# YOLOv8 model size:
#   yolov8n.pt  → Nano   (fastest, least accurate, ~6 MB)   ← good for testing
#   yolov8s.pt  → Small  (balanced)
#   yolov8m.pt  → Medium (better accuracy)
MODEL_NAME = "yolov8n.pt"

# Minimum confidence score to show a detection (0.0 to 1.0)
CONFIDENCE_THRESHOLD = 0.15

# YOLO class IDs for vehicles only (from COCO dataset)
# 2=car, 3=motorcycle, 5=bus, 7=truck
VEHICLE_CLASSES = [2, 3, 5, 7]

# Label names to display on screen
CLASS_NAMES = {
    2: "Car",
    3: "Motorcycle",
    5: "Bus",
    7: "Truck"
}

# Bounding box colors per class (BGR format)
CLASS_COLORS = {
    2: (0, 255, 0),    # Car        → Green
    3: (255, 128, 0),  # Motorcycle → Orange
    5: (0, 0, 255),    # Bus        → Red
    7: (255, 0, 255),  # Truck      → Magenta
}

# -----------------------------------------------------------------------------
# VehicleDetector CLASS
# -----------------------------------------------------------------------------

class VehicleDetector:
    """
    Detects vehicles in video frames using YOLOv8.
    """

    def __init__(self, model_name=MODEL_NAME, confidence=CONFIDENCE_THRESHOLD):
        """Load the YOLO model. Downloads automatically on first run."""
        print(f"\n[INFO] Loading YOLOv8 model: {model_name}")
        print("[INFO] (First run will download the model — ~6 MB)\n")
        self.model      = YOLO(model_name)
        self.confidence = confidence
        print(f"[INFO] Model loaded successfully!")
        print(f"[INFO] Confidence threshold : {confidence}")
        print(f"[INFO] Detecting classes    : Car, Motorcycle, Bus, Truck\n")

    def detect(self, frame):
        """
        Run YOLOv8 detection on a single frame.

        Args:
            frame : numpy array (BGR image from OpenCV)

        Returns:
            detections : list of dicts, each containing:
                {
                  'bbox'      : [x1, y1, x2, y2]  pixel coordinates
                  'class_id'  : int
                  'class_name': str
                  'confidence': float
                }
        """
        results = self.model(
            frame,
            conf=self.confidence,
            classes=VEHICLE_CLASSES,
            verbose=False        # suppress per-frame console spam
        )

        detections = []
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                if class_id not in VEHICLE_CLASSES:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                confidence      = float(box.conf[0])

                detections.append({
                    "bbox"      : [x1, y1, x2, y2],
                    "class_id"  : class_id,
                    "class_name": CLASS_NAMES.get(class_id, "Vehicle"),
                    "confidence": round(confidence, 2),
                })

        return detections

    def draw(self, frame, detections):
        """
        Draw bounding boxes and labels onto a frame.

        Args:
            frame      : original BGR frame
            detections : list returned by detect()

        Returns:
            frame with boxes + labels drawn on it
        """
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            class_id        = det["class_id"]
            label           = f"{det['class_name']}  {det['confidence']:.0%}"
            color           = CLASS_COLORS.get(class_id, (200, 200, 200))

            # Bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Label background pill
            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(frame, (x1, y1 - text_h - 10), (x1 + text_w + 8, y1), color, -1)

            # Label text
            cv2.putText(
                frame, label,
                (x1 + 4, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (255, 255, 255), 2
            )

        # Vehicle count overlay (top-left corner)
        count_text = f"Vehicles detected: {len(detections)}"
        cv2.putText(
            frame, count_text,
            (15, 35),
            cv2.FONT_HERSHEY_SIMPLEX, 1.0,
            (0, 255, 255), 2
        )

        return frame


# -----------------------------------------------------------------------------
# RUN DETECTION ON VIDEO
# -----------------------------------------------------------------------------

def run_detection(video_source=VIDEO_SOURCE, output_path=OUTPUT_VIDEO):
    """
    Open a video, run detection on every frame, show live preview,
    and save annotated output video.
    """

    # ── Load detector ────────────────────────────────────────────────────────
    detector = VehicleDetector()

    # ── Open video source ────────────────────────────────────────────────────
    cap = cv2.VideoCapture(video_source)

    if not cap.isOpened():
        print(f"[ERROR] Cannot open video: {video_source}")
        print("[TIP]  Make sure the file exists in test_data/videos/")
        print("[TIP]  Or change VIDEO_SOURCE = 0 at the top to use your webcam")
        return

    # Video properties
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS) or 30
    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"[INFO] Video     : {video_source}")
    print(f"[INFO] Resolution: {width} x {height}")
    print(f"[INFO] FPS       : {fps:.1f}")
    print(f"[INFO] Frames    : {total}")
    print(f"[INFO] Output    : {output_path}\n")
    print("[INFO] Press  Q  to quit the preview window\n")

    # ── Output video writer ──────────────────────────────────────────────────
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # ── Process frame by frame ───────────────────────────────────────────────
    frame_num = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_num += 1

        # Run detection
        detections = detector.detect(frame)

        # Draw boxes on frame
        annotated = detector.draw(frame.copy(), detections)

        # Frame counter overlay (bottom-left)
        cv2.putText(
            annotated,
            f"Frame: {frame_num}/{total}",
            (15, height - 15),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6,
            (200, 200, 200), 1
        )

        # Write to output video
        writer.write(annotated)

        # Show live preview
        cv2.imshow("Phase 2 — Vehicle Detection (Press Q to quit)", annotated)

        # Print progress every 30 frames
        if frame_num % 30 == 0 or frame_num == 1:
            n = len(detections)
            print(f"  Frame {frame_num:>5}/{total}  |  Vehicles detected: {n}")

        # Press Q to quit early
        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("\n[INFO] Stopped early by user (Q pressed)")
            break

    # ── Cleanup ──────────────────────────────────────────────────────────────
    cap.release()
    writer.release()
    cv2.destroyAllWindows()

    print(f"\n[DONE] Detection complete!")
    print(f"[DONE] Output saved to: {output_path}")
    print(f"[DONE] Total frames processed: {frame_num}")
    print("\n✅  Phase 2 complete — ready for Phase 3 (Vehicle Tracking)\n")


# -----------------------------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    run_detection()
