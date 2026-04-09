# =============================================================================
#  Traffic Violation Detection System
#  FILE : detection/plate_detector.py
#  PHASE: 5 + 6 — License Plate Detection + OCR (EasyOCR)
#
#  WHAT THIS FILE DOES:
#    - Takes each vehicle's bounding box from the tracker
#    - Crops the lower portion of the vehicle (where the plate is)
#    - Preprocesses the cropped image for better OCR accuracy
#    - Uses EasyOCR to read the plate text
#    - Saves plate images to media/violations/
#    - Returns clean plate text like "MH12AB1234"
#
#  HOW TO RUN (standalone test):
#    python detection/plate_detector.py
# =============================================================================

import cv2
import easyocr
import numpy as np
import os
import re
from datetime import datetime

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------

# Where to save cropped plate images
PLATE_SAVE_DIR = "media/violations/plates"

# Minimum OCR confidence to accept a reading (0.0 to 1.0)
MIN_OCR_CONFIDENCE = 0.2

# How much of the vehicle bounding box (from bottom) to crop as plate region
# 0.35 = bottom 35% of the vehicle box — works for most top-down videos
PLATE_CROP_RATIO = 0.35

# EasyOCR language — 'en' for English/Latin plates
OCR_LANGUAGES = ['en']

# -----------------------------------------------------------------------------
# PlateDetector CLASS
# -----------------------------------------------------------------------------

class PlateDetector:
    """
    Detects and reads license plates from vehicle bounding boxes.
    Combines Phase 5 (plate region crop) and Phase 6 (OCR reading).
    """

    def __init__(self):
        print("\n[INFO] Loading EasyOCR reader...")
        print("[INFO] (First run downloads OCR models ~100 MB — please wait)\n")
        self.reader    = easyocr.Reader(OCR_LANGUAGES, gpu=False, verbose=False)
        self.plate_dir = PLATE_SAVE_DIR
        os.makedirs(self.plate_dir, exist_ok=True)
        print("[INFO] EasyOCR loaded successfully!\n")

        # Cache: {track_id: plate_text} — avoid re-running OCR on same vehicle
        self.plate_cache = {}

    # ── Phase 5: Crop plate region ────────────────────────────────────────────

    def crop_plate_region(self, frame, bbox):
        """
        Crop the plate region from the vehicle bounding box.

        For a top-down camera, the license plate is at the REAR of the vehicle
        which appears at the BOTTOM of the bounding box.

        Args:
            frame : full video frame (BGR numpy array)
            bbox  : [x1, y1, x2, y2] vehicle bounding box

        Returns:
            plate_crop : cropped BGR image of the plate region
                         or None if the crop is too small
        """
        x1, y1, x2, y2 = bbox
        h = y2 - y1
        w = x2 - x1

        # Only use bottom PLATE_CROP_RATIO of the vehicle box
        plate_y1 = int(y2 - h * PLATE_CROP_RATIO)
        plate_y2 = y2

        # Safety clamp to frame boundaries
        frame_h, frame_w = frame.shape[:2]
        plate_y1 = max(0, plate_y1)
        plate_y2 = min(frame_h, plate_y2)
        x1_safe  = max(0, x1)
        x2_safe  = min(frame_w, x2)

        crop = frame[plate_y1:plate_y2, x1_safe:x2_safe]

        # Reject crops that are too small to read
        if crop.shape[0] < 10 or crop.shape[1] < 20:
            return None

        return crop

    # ── Phase 6: Preprocess + OCR ─────────────────────────────────────────────

    def preprocess(self, plate_img):
        """
        Preprocess the plate image to improve OCR accuracy.

        Steps:
          1. Convert to grayscale
          2. Upscale 3x (EasyOCR works better on larger images)
          3. Apply adaptive threshold to handle shadows and lighting
          4. Denoise
        """
        # Grayscale
        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)

        # Upscale — makes characters much clearer for OCR
        scale  = 3
        width  = gray.shape[1] * scale
        height = gray.shape[0] * scale
        gray   = cv2.resize(gray, (width, height), interpolation=cv2.INTER_CUBIC)

        # Denoise
        gray = cv2.fastNlMeansDenoising(gray, h=10)

        # Adaptive threshold — handles uneven lighting better than simple threshold
        thresh = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        # Convert back to BGR for EasyOCR
        processed = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
        return processed

    def read_plate(self, plate_img):
        """
        Run EasyOCR on the preprocessed plate image.

        Returns:
            plate_text : cleaned plate string e.g. "MH12AB1234"
                         or "" if nothing readable found
        """
        if plate_img is None:
            return ""

        processed = self.preprocess(plate_img)

        try:
            results = self.reader.readtext(processed)
        except Exception as e:
            return ""

        if not results:
            return ""

        # Collect text from confident detections
        texts = []
        for (bbox_pts, text, confidence) in results:
            if confidence >= MIN_OCR_CONFIDENCE:
                texts.append(text)

        if not texts:
            return ""

        # Join all detected text segments
        raw_text = " ".join(texts)

        # Clean: keep only letters, numbers, spaces
        cleaned = re.sub(r"[^A-Z0-9 ]", "", raw_text.upper()).strip()

        # Remove single characters (noise)
        parts   = [p for p in cleaned.split() if len(p) > 1]
        cleaned = "".join(parts)

        return cleaned if len(cleaned) >= 3 else ""

    # ── Main method: detect plate for a vehicle ───────────────────────────────

    def get_plate(self, frame, track_id, bbox, save_image=False):
        """
        Full pipeline: crop → preprocess → OCR → return text.

        Uses cache so OCR only runs once per vehicle ID.

        Args:
            frame     : full video frame
            track_id  : vehicle track ID (for caching)
            bbox      : [x1, y1, x2, y2]
            save_image: if True, saves the plate crop to disk

        Returns:
            plate_text : string like "34AIE791" or "" if not readable
        """
        tid = str(track_id)

        # Return cached result if already read for this vehicle
        if tid in self.plate_cache and self.plate_cache[tid]:
            return self.plate_cache[tid]

        # Crop plate region
        plate_crop = self.crop_plate_region(frame, bbox)
        if plate_crop is None:
            return ""

        # Run OCR
        plate_text = self.read_plate(plate_crop)

        # Cache result
        if plate_text:
            self.plate_cache[tid] = plate_text

            # Optionally save the plate image
            if save_image:
                timestamp = datetime.now().strftime("%H%M%S")
                filename  = f"{self.plate_dir}/plate_{tid}_{plate_text}_{timestamp}.jpg"
                cv2.imwrite(filename, plate_crop)

        return plate_text

    def draw_plate(self, frame, bbox, plate_text):
        """
        Draw the plate text below the vehicle bounding box.
        """
        if not plate_text:
            return frame

        x1, y1, x2, y2 = bbox

        # Background bar below the box
        label  = f"PLATE: {plate_text}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(frame, (x1, y2), (x1 + tw + 8, y2 + th + 10), (255, 165, 0), -1)
        cv2.putText(frame, label, (x1 + 4, y2 + th + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        return frame


# -----------------------------------------------------------------------------
# STANDALONE TEST — run on a single frame from your traffic video
# -----------------------------------------------------------------------------

def run_plate_test():
    """
    Quick test: extract a frame from the traffic video,
    find vehicles using YOLO, and try to read their plates.
    """
    from ultralytics import YOLO

    VIDEO_SOURCE = "test_data/videos/traffic.mp4"
    CONFIDENCE   = 0.15
    VEHICLE_CLS  = [2, 3, 5, 7]
    CLASS_NAMES  = {2: "Car", 3: "Motorcycle", 5: "Bus", 7: "Truck"}

    print("\n" + "="*55)
    print("  Phase 5+6 — License Plate Detection Test")
    print("="*55 + "\n")

    # Load detector
    detector = PlateDetector()
    model    = YOLO("yolov8n.pt")

    # Open video
    cap   = cv2.VideoCapture(VIDEO_SOURCE)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"[INFO] Video: {VIDEO_SOURCE}")
    print(f"[INFO] Total frames: {total}")
    print("[INFO] Testing plate reading on multiple frames...\n")

    plates_found = []
    tested       = 0

    # Test on frames spread across the video
    test_frames = [30, 60, 90, 120, 150, 180]

    for frame_idx in test_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            continue

        results = model(frame, conf=CONFIDENCE, classes=VEHICLE_CLS, verbose=False)

        for result in results:
            for i, box in enumerate(result.boxes):
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cid             = int(box.cls[0])
                class_name      = CLASS_NAMES.get(cid, "Vehicle")
                bbox            = [x1, y1, x2, y2]
                fake_tid        = f"{frame_idx}_{i}"

                # Try to read plate
                plate = detector.get_plate(frame, fake_tid, bbox, save_image=True)
                tested += 1

                if plate:
                    plates_found.append(plate)
                    print(f"  ✅ Frame {frame_idx:>3} | {class_name:12s} | "
                          f"Plate: {plate}")
                    # Draw on frame
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    frame = detector.draw_plate(frame, bbox, plate)

        # Save annotated frame
        out_path = f"test_data/images/plate_test_frame{frame_idx}.jpg"
        os.makedirs("test_data/images", exist_ok=True)
        cv2.imwrite(out_path, frame)

    cap.release()

    # Summary
    print(f"\n{'='*55}")
    print(f"  Plate Detection Results")
    print(f"{'='*55}")
    print(f"  Vehicles tested     : {tested}")
    print(f"  Plates read         : {len(plates_found)}")
    print(f"  Success rate        : {len(plates_found)/tested*100:.0f}%" if tested else "  No vehicles found")
    print(f"  Plates found        : {set(plates_found)}")
    print(f"  Images saved to     : test_data/images/")
    print(f"  Plate crops saved   : {PLATE_SAVE_DIR}/")
    print(f"\n✅  Phase 5+6 complete — ready for Phase 7 (Full Pipeline)\n")


# -----------------------------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    run_plate_test()
