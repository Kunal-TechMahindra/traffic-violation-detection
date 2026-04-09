# =============================================================================
#  Traffic Violation Detection System
#  FILE : detection/pipeline.py  (FULLY FIXED)
#
#  3 FIXES APPLIED:
#  FIX 1 — Removed duplicate OCR loading code (was loaded twice before)
#  FIX 2 — OCR now runs AFTER the full video loop ends (no mid-video freeze)
#           Video plays smoothly through all 239 frames
#           Then OCR runs on all violation frames at the end
#  FIX 3 — ocr.py now uses CRAFT instead of dbnet18 (no compiler needed)
# =============================================================================

import cv2
import csv
import os
import sys
import requests
from datetime import datetime
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort

VIDEO_SOURCE         = "test_data/videos/traffic.mp4"
OUTPUT_VIDEO         = "test_data/videos/output_phase7.mp4"
OUTPUT_CSV           = "logs/violations.csv"
VIOLATIONS_IMAGE_DIR = "media/violations"
MODEL_NAME           = "yolov8n.pt"
LINE_Y1              = 1350
LINE_Y2              = 550
REAL_DISTANCE_METERS = 8.0
SPEED_LIMIT_KMPH     = 80
MIN_FRAMES           = 5
CONFIDENCE           = 0.15
VEHICLE_CLASSES      = [2, 3, 5, 7]
CLASS_NAMES          = {2:"Car", 3:"Motorcycle", 5:"Bus", 7:"Truck"}
DJANGO_API_URL       = "http://127.0.0.1:8000/api/upload-violation/"
SAVE_TO_API          = True

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from detection.ocr import read_plate, get_ocr_reader
    print("[INFO] OCR module loaded")
except ImportError:
    def read_plate(frame, bbox): return ""
    def get_ocr_reader(): return None, "none"
    print("[WARN] OCR not found — plates will show UNKNOWN")


class ViolationPipeline:

    def __init__(self, fps):
        self.fps             = fps
        self.model           = YOLO(MODEL_NAME)
        self.tracker         = DeepSort(max_age=30, n_init=2,
                                        nms_max_overlap=1.0,
                                        max_cosine_distance=0.3)
        self.vehicle_data    = {}
        self.violations      = []        # list of violation dicts
        self.best_frame_data = {}        # tid -> {frame, bbox, area}
        os.makedirs(VIOLATIONS_IMAGE_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

    def process_frame(self, frame, frame_num):
        """
        FIX 2: During the video loop, we ONLY do detection + tracking + speed.
        We do NOT call read_plate() here — that happens AFTER the video ends.
        This keeps the video window smooth and responsive.
        """
        # ── YOLO Detection ────────────────────────────────────────────────────
        results  = self.model(frame, conf=CONFIDENCE,
                              classes=VEHICLE_CLASSES, verbose=False)
        raw_dets = []
        for r in results:
            for box in r.boxes:
                cid = int(box.cls[0])
                if cid not in VEHICLE_CLASSES: continue
                x1,y1,x2,y2 = map(int, box.xyxy[0])
                raw_dets.append(([x1,y1,x2-x1,y2-y1], float(box.conf[0]), cid))

        # ── DeepSORT Tracking ─────────────────────────────────────────────────
        tracks = self.tracker.update_tracks(raw_dets, frame=frame)
        active = []

        for track in tracks:
            if not track.is_confirmed(): continue
            tid        = str(track.track_id)
            x1,y1,x2,y2 = map(int, track.to_ltrb())
            cx, cy     = (x1+x2)//2, (y1+y2)//2
            cid        = track.get_det_class()
            cname      = CLASS_NAMES.get(cid,"Vehicle") if cid else "Vehicle"
            bbox       = [x1,y1,x2,y2]

            # Keep track of the LARGEST frame seen per vehicle
            # (largest = vehicle closest to camera = sharpest plate image)
            area = (x2-x1)*(y2-y1)
            if tid not in self.best_frame_data or area > self.best_frame_data[tid]["area"]:
                self.best_frame_data[tid] = {
                    "frame": frame.copy(),
                    "bbox" : bbox,
                    "area" : area,
                }

            if tid not in self.vehicle_data:
                self.vehicle_data[tid] = {
                    "frame_A":None,"frame_B":None,
                    "speed":None,"violation":False,
                    "plate":"","class":cname,
                }

            rec = self.vehicle_data[tid]

            # ── Line crossing ─────────────────────────────────────────────────
            if rec["frame_A"] is None and LINE_Y2 <= cy <= LINE_Y1:
                rec["frame_A"] = frame_num
            if rec["frame_A"] and not rec["frame_B"] and cy <= LINE_Y2:
                rec["frame_B"] = frame_num

            # ── Speed calculation ─────────────────────────────────────────────
            if rec["frame_A"] and rec["frame_B"] and rec["speed"] is None:
                elapsed = int(rec["frame_B"]) - int(rec["frame_A"])
                if elapsed >= MIN_FRAMES:
                    spd = (REAL_DISTANCE_METERS / (elapsed / self.fps)) * 3.6
                    if spd <= 200:
                        rec["speed"] = round(spd, 1)
                        if spd > SPEED_LIMIT_KMPH:
                            rec["violation"] = True
                            # ── FIX 2: Store violation for OCR LATER ──────────
                            # DO NOT call read_plate() here — saves for after video
                            self.violations.append({
                                "track_id" : tid,
                                "class_name": cname,
                                "speed"    : rec["speed"],
                                "plate"    : "",          # filled after video
                                "frame"    : frame_num,
                                "image_path": "",         # filled after video
                                "timestamp": datetime.now().strftime("%H:%M:%S"),
                            })
                            print(f"\n  VIOLATION DETECTED! {cname}#{tid} "
                                  f"{spd:.1f}km/h — plate will be read after video\n")
                        else:
                            print(f"  {cname}#{tid} -> {rec['speed']}km/h  OK")
                else:
                    rec["frame_A"] = None
                    rec["frame_B"] = None

            active.append({
                "tid":tid,"cname":cname,"bbox":bbox,
                "center":(cx,cy),"speed":rec["speed"],
                "violation":rec["violation"],"plate":rec["plate"],
            })

        return self._draw(frame, active, frame_num)

    def run_ocr_on_violations(self):
        """
        FIX 2: Run OCR on all violations AFTER video loop finishes.
        Video plays at full speed — no freezing.
        """
        if not self.violations:
            print("[INFO] No violations to read plates for.")
            return

        print(f"\n[OCR] Reading plates for {len(self.violations)} violations...")

        for v in self.violations:
            tid  = v["track_id"]
            best = self.best_frame_data.get(tid, {})
            bf   = best.get("frame")
            bb   = best.get("bbox")

            if bf is None or bb is None:
                v["plate"] = "UNKNOWN"
                continue

            print(f"[OCR] Reading plate for {v['class_name']}#{tid}...")
            plate = read_plate(bf, bb)
            v["plate"] = plate if plate else "UNKNOWN"
            print(f"[OCR] Result: {v['plate']}")

            # Save evidence image with correct plate name
            img_path = self._save_evidence(
                bf, bb, tid, v["speed"], v["plate"]
            )
            v["image_path"] = img_path

            # Save to Django DB
            self._save_to_api(
                tid, v["class_name"], v["speed"],
                v["plate"], v["frame"], img_path
            )

    def _save_evidence(self, frame, bbox, tid, speed, plate):
        x1,y1,x2,y2 = bbox
        pad  = 20
        crop = frame[max(0,y1-pad):min(frame.shape[0],y2+pad),
                     max(0,x1-pad):min(frame.shape[1],x2+pad)].copy()
        ts   = datetime.now().strftime("%H%M%S")
        name = f"violation_{tid}_{speed}kmh_{plate}_{ts}.jpg"
        path = os.path.join(VIOLATIONS_IMAGE_DIR, name)
        cv2.imwrite(path, crop)
        return path

    def _save_to_api(self, tid, cname, speed, plate, frame_num, img_path=None):
        if not SAVE_TO_API: return
        try:
            data = {
                "track_id"    : tid,
                "vehicle_type": cname,
                "plate"       : plate,
                "speed"       : speed,
                "speed_limit" : SPEED_LIMIT_KMPH,
                "frame_number": frame_num,
                "video_source": os.path.basename(VIDEO_SOURCE),
            }
            files = ({"image": open(img_path,"rb")}
                     if img_path and os.path.exists(img_path) else None)
            r = requests.post(DJANGO_API_URL, data=data, files=files, timeout=5)
            if r.status_code == 201:
                vid = r.json().get("violation",{}).get("id")
                print(f"  [DB] Saved to database — ID:{vid}  Plate:{plate}")
            else:
                print(f"  [DB] Save failed: {r.status_code} — {r.text[:100]}")
        except Exception as e:
            print(f"  [DB] Could not reach API: {e}")

    def _draw(self, frame, active, frame_num):
        h,w = frame.shape[:2]
        cv2.line(frame,(0,LINE_Y1),(w,LINE_Y1),(0,255,255),2)
        cv2.putText(frame,"Line A",(10,LINE_Y1-8),
                    cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,255,255),2)
        cv2.line(frame,(0,LINE_Y2),(w,LINE_Y2),(0,165,255),2)
        cv2.putText(frame,"Line B",(10,LINE_Y2-8),
                    cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,165,255),2)
        for t in active:
            x1,y1,x2,y2 = t["bbox"]
            color = ((0,0,255) if t["violation"] else
                     (0,255,0) if t["speed"] else (200,200,200))
            cv2.rectangle(frame,(x1,y1),(x2,y2),color,2)
            if t["violation"]:
                label = f"{t['cname']}#{t['tid']} {t['speed']}km/h VIOLATION!"
            elif t["speed"]:
                label = f"{t['cname']}#{t['tid']} {t['speed']}km/h"
            else:
                label = f"{t['cname']}#{t['tid']}"
            (tw,th),_ = cv2.getTextSize(label,cv2.FONT_HERSHEY_SIMPLEX,0.5,2)
            cv2.rectangle(frame,(x1,y1-th-10),(x1+tw+8,y1),color,-1)
            cv2.putText(frame,label,(x1+4,y1-5),
                        cv2.FONT_HERSHEY_SIMPLEX,0.5,(255,255,255),2)
        viols  = len(self.violations)
        speeds = sum(1 for v in self.vehicle_data.values() if v["speed"])
        cv2.rectangle(frame,(0,0),(w,50),(0,0,0),-1)
        cv2.putText(frame,
            f"Frame:{frame_num}  Tracked:{len(self.vehicle_data)}"
            f"  Speeds:{speeds}  Violations:{viols}",
            (10,32),cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,255,255),2)
        return frame

    def save_csv(self):
        if not self.violations: return
        with open(OUTPUT_CSV,"w",newline="") as f:
            w = csv.DictWriter(f,fieldnames=[
                "track_id","class_name","speed","plate","frame","timestamp"
            ])
            w.writeheader()
            for v in self.violations: w.writerow({k:v[k] for k in w.fieldnames})
        print(f"[SAVED] {len(self.violations)} violations → {OUTPUT_CSV}")


# =============================================================================
# MAIN
# =============================================================================

def run_pipeline():
    print("\n" + "="*60)
    print("  Traffic Violation Detection System — Full Pipeline")
    print("="*60 + "\n")

    cap = cv2.VideoCapture(VIDEO_SOURCE)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open: {VIDEO_SOURCE}"); return

    fps    = cap.get(cv2.CAP_PROP_FPS) or 30
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"[INFO] Video   : {VIDEO_SOURCE}")
    print(f"[INFO] FPS     : {fps:.1f}")
    print(f"[INFO] Frames  : {total}")
    print(f"[INFO] Lines   : A={LINE_Y1}px  B={LINE_Y2}px")
    print(f"[INFO] Limit   : {SPEED_LIMIT_KMPH} km/h")
    print()

    # ── FIX 1: Only ONE OCR pre-load (duplicate removed) ─────────────────────
    print("[INFO] Pre-loading EasyOCR (please wait ~20 seconds)...")
    get_ocr_reader()
    print("[INFO] EasyOCR ready!\n")
    print("[INFO] Starting video — press Q to quit")
    print("-"*60)

    pipeline  = ViolationPipeline(fps)
    fourcc    = cv2.VideoWriter_fourcc(*"mp4v")
    writer    = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, fps, (width, height))
    frame_num = 0

    # ── FIX 2: Video loop — NO OCR here, just detection+tracking+speed ───────
    while True:
        ret, frame = cap.read()
        if not ret: break
        frame_num += 1

        annotated = pipeline.process_frame(frame, frame_num)
        writer.write(annotated)
        cv2.imshow("Traffic Violation Detection (Q to quit)", annotated)

        if frame_num % 30 == 0:
            v = len(pipeline.violations)
            s = sum(1 for x in pipeline.vehicle_data.values() if x["speed"])
            print(f"  Frame {frame_num:>3}/{total}  "
                  f"Tracked:{len(pipeline.vehicle_data)}  "
                  f"Speeds:{s}  Violations:{v}")

        if cv2.waitKey(10) & 0xFF == ord("q"):
            print("\n[INFO] Stopped by user")
            break

    cap.release()
    writer.release()
    cv2.destroyAllWindows()

    print(f"\n[INFO] Video complete! {frame_num} frames processed.")
    print(f"[INFO] Violations detected: {len(pipeline.violations)}")

    # ── FIX 2: Run OCR now — video is done, no freezing ──────────────────────
    print("\n" + "-"*60)
    pipeline.run_ocr_on_violations()

    pipeline.save_csv()

    # ── Final Summary ─────────────────────────────────────────────────────────
    speeds = [v["speed"] for v in pipeline.vehicle_data.values() if v["speed"]]
    print(f"\n{'='*60}")
    print(f"  FINAL RESULTS")
    print(f"{'='*60}")
    print(f"  Vehicles tracked   : {len(pipeline.vehicle_data)}")
    print(f"  Speeds calculated  : {len(speeds)}")
    print(f"  Violations found   : {len(pipeline.violations)}")
    if speeds:
        print(f"  Highest speed      : {max(speeds)} km/h")
        print(f"  Average speed      : {sum(speeds)/len(speeds):.1f} km/h")
    print()
    for v in pipeline.violations:
        print(f"  {v['class_name']:12} #{v['track_id']:<4}  "
              f"{v['speed']} km/h  Plate: {v['plate']}  @ {v['timestamp']}")
    print(f"\n  Output video : {OUTPUT_VIDEO}")
    print(f"  CSV          : {OUTPUT_CSV}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run_pipeline()
