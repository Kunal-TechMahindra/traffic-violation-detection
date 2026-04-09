# ─────────────────────────────────────────────────────────────────────────────
#  Traffic Violation Detection System
#  FILE: setup_project.py
#
#  HOW TO RUN:
#    1. Open this file in VS Code
#    2. Open Terminal  →  python setup_project.py
#    3. This will create the full project folder structure
# ─────────────────────────────────────────────────────────────────────────────

import os

# ── Define all folders to create ─────────────────────────────────────────────

FOLDERS = [
    # Core detection modules
    "detection",
    "detection/models",          # store YOLOv8 .pt weight files here

    # Django backend
    "backend",
    "backend/api",               # Django REST API app
    "backend/api/migrations",    # Django DB migrations (auto-generated)

    # Media & outputs
    "media",
    "media/uploads",             # user-uploaded videos
    "media/violations",          # saved violation frame images

    # Test inputs
    "test_data",
    "test_data/videos",          # put traffic test videos here
    "test_data/images",          # test images for Phase 2

    # Logs
    "logs",
]

# ── Define all placeholder files to create ───────────────────────────────────

FILES = {
    # Detection pipeline
    "detection/__init__.py":         "# Detection package\n",
    "detection/detector.py":         "# Phase 2 — YOLOv8 vehicle detection\n",
    "detection/tracker.py":          "# Phase 3 — DeepSORT vehicle tracking\n",
    "detection/speed.py":            "# Phase 4 — Speed calculation logic\n",
    "detection/plate_detector.py":   "# Phase 5 — License plate detection\n",
    "detection/ocr.py":              "# Phase 6 — EasyOCR plate text reading\n",
    "detection/pipeline.py":         "# Phase 7 — Full violation pipeline\n",

    # Django backend
    "backend/__init__.py":           "# Backend package\n",
    "backend/api/__init__.py":       "# API app\n",
    "backend/api/models.py":         "# Phase 8 — Violation database model\n",
    "backend/api/serializers.py":    "# Phase 9 — DRF serializers\n",
    "backend/api/views.py":          "# Phase 9 — API views / endpoints\n",
    "backend/api/urls.py":           "# Phase 9 — URL routing\n",
    "backend/api/tasks.py":          "# Phase 10 — Celery async tasks\n",
    "backend/api/migrations/__init__.py": "",

    # Config files
    ".env":                          "# Environment variables (never commit this)\nDEBUG=True\nSECRET_KEY=change-me-in-production\nDB_NAME=traffic_db\nDB_USER=postgres\nDB_PASSWORD=your_password\nDB_HOST=localhost\nDB_PORT=5432\nREDIS_URL=redis://localhost:6379/0\nSPEED_LIMIT_KMPH=80\n",
    ".gitignore":                    "venv/\n__pycache__/\n*.pyc\n.env\nmedia/\nlogs/\n*.pt\n",
    "README.md":                     "# Traffic Violation Detection System\n\nEnd-to-end system for detecting vehicle speed violations using YOLOv8, DeepSORT, EasyOCR, Django REST API, Celery, and React.\n\n## Phases\n1. Environment Setup\n2. Vehicle Detection (YOLOv8)\n3. Vehicle Tracking (DeepSORT)\n4. Speed Detection\n5. License Plate Detection\n6. OCR (EasyOCR)\n7. Violation Pipeline\n8. Database (PostgreSQL)\n9. Django REST API\n10. Async Processing (Celery + Redis)\n11. Dashboard (React)\n12. Deployment (Docker + AWS)\n",
    "main.py":                       "# ─────────────────────────────────────────\n# Traffic Violation Detection System\n# Entry point — run detection on a video\n# ─────────────────────────────────────────\n# Usage: python main.py --video test_data/videos/your_video.mp4\n\nimport argparse\n\nif __name__ == '__main__':\n    parser = argparse.ArgumentParser(description='Traffic Violation Detector')\n    parser.add_argument('--video', type=str, required=True, help='Path to input video')\n    args = parser.parse_args()\n    print(f'[INFO] Processing video: {args.video}')\n    # detection pipeline will be wired here in Phase 7\n",
}

# ── Create folders ────────────────────────────────────────────────────────────

print("\n📁 Creating project folders...\n")
for folder in FOLDERS:
    os.makedirs(folder, exist_ok=True)
    print(f"  ✅ {folder}/")

# ── Create files ──────────────────────────────────────────────────────────────

print("\n📄 Creating project files...\n")
for filepath, content in FILES.items():
    # Only create if it doesn't already exist (safe to re-run)
    if not os.path.exists(filepath):
        with open(filepath, "w") as f:
            f.write(content)
        print(f"  ✅ {filepath}")
    else:
        print(f"  ⏭️  {filepath}  (already exists, skipped)")

# ── Done ──────────────────────────────────────────────────────────────────────

print("\n" + "─" * 55)
print("✅  Project structure created successfully!\n")
print("📌  Next steps:")
print("   1. Run:  pip install -r requirements.txt")
print("   2. Run:  python verify_setup.py")
print("   3. Move to Phase 2 → detection/detector.py")
print("─" * 55 + "\n")
