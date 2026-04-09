# ─────────────────────────────────────────────────────────────────────────────
#  Traffic Violation Detection System
#  FILE: verify_setup.py
#
#  HOW TO RUN  (after pip install -r requirements.txt):
#    python verify_setup.py
#
#  This checks every library is correctly installed and shows
#  their versions so you know exactly what you're working with.
# ─────────────────────────────────────────────────────────────────────────────

import sys

print("\n" + "=" * 55)
print("  Traffic Violation System — Environment Check")
print("=" * 55)

# ── Python version ────────────────────────────────────────────────────────────

py = sys.version_info
print(f"\n🐍 Python version : {py.major}.{py.minor}.{py.micro}", end="")
if py.major == 3 and py.minor >= 9:
    print("  ✅")
else:
    print("  ❌  (Need Python 3.9+)")

# ── Library checks ────────────────────────────────────────────────────────────

LIBRARIES = [
    ("cv2",               "opencv-python",          "Computer Vision"),
    ("ultralytics",       "ultralytics (YOLOv8)",   "Vehicle Detection"),
    ("deep_sort_realtime","deep-sort-realtime",      "Vehicle Tracking"),
    ("easyocr",           "easyocr",                "License Plate OCR"),
    ("numpy",             "numpy",                  "Array Operations"),
    ("pandas",            "pandas",                 "Data Handling"),
    ("matplotlib",        "matplotlib",             "Plotting"),
    ("PIL",               "Pillow",                 "Image Utils"),
    ("django",            "Django",                 "Web Framework"),
    ("rest_framework",    "djangorestframework",     "REST API"),
    ("corsheaders",       "django-cors-headers",    "CORS Headers"),
    ("dotenv",            "python-dotenv",           "Env Variables"),
    ("psycopg2",          "psycopg2-binary",         "PostgreSQL Driver"),
    ("celery",            "celery",                 "Async Tasks"),
    ("redis",             "redis",                  "Redis / Celery Broker"),
]

print("\n📦 Checking installed packages:\n")
all_ok = True
for import_name, package_name, purpose in LIBRARIES:
    try:
        mod = __import__(import_name)
        version = getattr(mod, "__version__", "installed")
        print(f"  ✅  {package_name:<30}  {version:<12}  ({purpose})")
    except ImportError:
        print(f"  ❌  {package_name:<30}  NOT FOUND     ({purpose})")
        all_ok = False

# ── Quick functional test ─────────────────────────────────────────────────────

print("\n🔬 Quick functional tests:\n")

# OpenCV — can we read a blank frame?
try:
    import cv2
    import numpy as np
    blank = np.zeros((100, 100, 3), dtype=np.uint8)
    gray  = cv2.cvtColor(blank, cv2.COLOR_BGR2GRAY)
    print("  ✅  OpenCV  — frame processing works")
except Exception as e:
    print(f"  ❌  OpenCV  — {e}")

# NumPy
try:
    import numpy as np
    arr = np.array([1, 2, 3]) * 3.6
    print("  ✅  NumPy   — array math works")
except Exception as e:
    print(f"  ❌  NumPy   — {e}")

# Ultralytics (don't download model, just check import)
try:
    from ultralytics import YOLO
    print("  ✅  YOLO    — ultralytics importable (model downloads on first use)")
except Exception as e:
    print(f"  ❌  YOLO    — {e}")

# EasyOCR (just import, don't load model)
try:
    import easyocr
    print("  ✅  EasyOCR — importable (model downloads on first use)")
except Exception as e:
    print(f"  ❌  EasyOCR — {e}")

# Django
try:
    import django
    django.setup.__doc__  # just access it
    print("  ✅  Django  — framework importable")
except Exception as e:
    print(f"  ❌  Django  — {e}")

# ── Final summary ─────────────────────────────────────────────────────────────

print("\n" + "=" * 55)
if all_ok:
    print("🎉  All packages installed! Phase 1 complete.")
    print("\n📌  Next step:")
    print("   Open  detection/detector.py  →  start Phase 2")
else:
    print("⚠️   Some packages missing. Fix them by running:")
    print("\n     pip install -r requirements.txt\n")
    print("   Then re-run:  python verify_setup.py")
print("=" * 55 + "\n")
