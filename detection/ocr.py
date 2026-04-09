# =============================================================================
#  FILE : detection/ocr.py  (FIXED — no C++ compiler needed)
#  FIX  : Removed detect_network="dbnet18" — now uses default CRAFT detector
#  CRAFT works on ALL Windows machines without Visual Studio / cl.exe
# =============================================================================

import cv2, re, os, numpy as np
os.environ["OMP_NUM_THREADS"] = "1"

_reader = None

def get_ocr_reader():
    global _reader
    if _reader is not None:
        return _reader, "easyocr"
    try:
        import easyocr
        print("[OCR] Loading EasyOCR (CRAFT detector — no compiler needed)...")
        # ── DO NOT pass detect_network="dbnet18" ──────────────────────────────
        # dbnet18 needs cl.exe (C++ compiler) — not installed on most Windows PCs
        # Default CRAFT detector works without any compiler
        # ──────────────────────────────────────────────────────────────────────
        _reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        print("[OCR] EasyOCR ready!")
        return _reader, "easyocr"
    except Exception as e:
        print(f"[OCR] EasyOCR failed: {e}")
        return None, "none"


def read_plate(frame, bbox):
    """Read plate text from vehicle bounding box. Tries 4 crop regions."""
    reader, engine = get_ocr_reader()
    if not reader:
        return ""

    x1,y1,x2,y2 = bbox
    h, fh, fw = y2-y1, frame.shape[0], frame.shape[1]

    regions = [
        (max(0,x1), max(0,int(y2-h*0.30)), min(fw,x2), min(fh,y2)),
        (max(0,x1), max(0,int(y2-h*0.40)), min(fw,x2), min(fh,y2)),
        (max(0,x1), max(0,int(y1+h*0.55)), min(fw,x2), min(fh,int(y1+h*0.82))),
        (max(0,x1), max(0,y1),             min(fw,x2), min(fh,y2)),
    ]

    best, best_score = "", 0
    for cx1,cy1,cx2,cy2 in regions:
        crop = frame[cy1:cy2, cx1:cx2]
        if crop.shape[0] < 8 or crop.shape[1] < 15:
            continue
        for img in _preprocess(crop):
            t, s = _ocr(img, reader)
            if s > best_score:
                best_score, best = s, t
        if best_score >= 4:
            break
    return best


def _preprocess(crop):
    out = []
    try:
        g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        g = cv2.resize(g, (g.shape[1]*3, g.shape[0]*3), interpolation=cv2.INTER_CUBIC)
        g = cv2.fastNlMeansDenoising(g, h=10)
        _, t = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        out.append(cv2.cvtColor(t, cv2.COLOR_GRAY2BGR))

        g2 = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        g2 = cv2.resize(g2, (g2.shape[1]*3, g2.shape[0]*3), interpolation=cv2.INTER_CUBIC)
        a  = cv2.adaptiveThreshold(g2, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY, 11, 2)
        out.append(cv2.cvtColor(a, cv2.COLOR_GRAY2BGR))

        u = cv2.resize(crop, (crop.shape[1]*3, crop.shape[0]*3),
                       interpolation=cv2.INTER_CUBIC)
        out.append(u)
    except Exception:
        pass
    return out


def _ocr(image, reader):
    try:
        results = reader.readtext(image)
        raw     = " ".join(t for (_,t,c) in results if c >= 0.1)
        cleaned = re.sub(r"[^A-Z0-9 ]", " ", raw.upper())
        parts   = [p for p in cleaned.split() if len(p) >= 2]
        result  = "".join(parts)
        if (len(result) < 3 or len(result) > 12
                or not any(c.isalpha() for c in result)
                or not any(c.isdigit() for c in result)):
            return "", 0
        return result, len(result)
    except Exception:
        return "", 0


if __name__ == "__main__":
    from ultralytics import YOLO
    VIDEO = "test_data/videos/traffic.mp4"
    print("\n=== OCR Test ===\n")
    model  = YOLO("yolov8n.pt")
    cap    = cv2.VideoCapture(VIDEO)
    total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    found, tested = [], 0
    for fi in range(5, total, total//20)[:20]:
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ret, frame = cap.read()
        if not ret: continue
        for r in model(frame, conf=0.15, classes=[2,3,5,7], verbose=False):
            for box in r.boxes:
                x1,y1,x2,y2 = map(int, box.xyxy[0])
                plate = read_plate(frame, [x1,y1,x2,y2])
                tested += 1
                if plate:
                    found.append(plate)
                    print(f"  Frame {fi:>3}  Plate: {plate}")
    cap.release()
    print(f"\n  Tested:{tested}  Found:{len(found)}  "
          f"Rate:{len(found)/tested*100 if tested else 0:.0f}%")
    print(f"  Plates: {set(found)}\n")
