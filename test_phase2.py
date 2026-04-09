# =============================================================================
#  Traffic Violation Detection System
#  FILE : test_phase2.py
#  PHASE: 2 — Quick Test (single image OR webcam snapshot)
#
#  Run this BEFORE the full video to make sure detection is working.
#
#  HOW TO RUN:
#    python test_phase2.py
# =============================================================================

import cv2
import os
from detection.detector import VehicleDetector

print("\n" + "="*55)
print("  Phase 2 — Vehicle Detection Quick Test")
print("="*55 + "\n")

# ── Create detector ───────────────────────────────────────────────────────────
detector = VehicleDetector()

# ── Try to grab a test image ──────────────────────────────────────────────────
# Option A: use a frame from your webcam
print("[INFO] Capturing test frame from webcam (press any key to capture)...")
cap = cv2.VideoCapture(0)

if cap.isOpened():
    print("[INFO] Webcam opened — showing preview...")
    print("[INFO] Press SPACE to capture a frame, or Q to skip webcam test\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[WARN] Could not read from webcam — skipping")
            break

        cv2.imshow("Webcam preview — press SPACE to capture, Q to skip", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord(' '):   # SPACE = capture
            test_frame = frame.copy()
            cap.release()
            cv2.destroyAllWindows()

            print("[INFO] Frame captured! Running detection...\n")

            # Run detection on captured frame
            detections = detector.detect(test_frame)
            annotated  = detector.draw(test_frame.copy(), detections)

            # Show result
            cv2.imshow("Detection Result — press any key to close", annotated)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

            # Save result
            os.makedirs("test_data/images", exist_ok=True)
            out_path = "test_data/images/test_result.jpg"
            cv2.imwrite(out_path, annotated)

            # Summary
            print(f"[RESULT] Vehicles found : {len(detections)}")
            for i, d in enumerate(detections, 1):
                print(f"  {i}. {d['class_name']:12s}  confidence: {d['confidence']:.0%}  "
                      f"box: {d['bbox']}")

            print(f"\n[SAVED] Result image → {out_path}")
            break

        elif key == ord('q'):   # Q = skip webcam
            cap.release()
            cv2.destroyAllWindows()
            print("[INFO] Webcam test skipped\n")
            break

else:
    print("[WARN] No webcam found — skipping webcam test\n")

# ── Check if a test video exists too ─────────────────────────────────────────
video_path = "test_data/videos/traffic.mp4"
if os.path.exists(video_path):
    print(f"\n[INFO] Found test video: {video_path}")
    print("[INFO] You can now run the full detection:")
    print("       python detection/detector.py\n")
else:
    print("\n" + "─"*55)
    print("[NEXT] To run full video detection:")
    print("  1. Put a traffic video in:  test_data/videos/")
    print("  2. Rename it to:            traffic.mp4")
    print("  3. Run:                     python detection/detector.py")
    print("")
    print("[TIP]  No video? Download a free one from:")
    print("       https://www.pexels.com/search/videos/traffic/")
    print("─"*55 + "\n")

print("="*55)
print("✅  Phase 2 test complete!")
print("="*55 + "\n")
