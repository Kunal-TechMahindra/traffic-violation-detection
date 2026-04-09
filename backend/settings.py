# =============================================================================
#  Traffic Violation Detection System
#  FILE : backend/settings.py
#  PHASE: 8 — Django Backend Configuration
#
#  HOW TO USE:
#    1. Copy this file to backend/settings.py
#    2. Run: python manage.py makemigrations api
#    3. Run: python manage.py migrate
#    4. Run: python manage.py createsuperuser
#    5. Run: python manage.py runserver
# =============================================================================

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = ["*"]

# -----------------------------------------------------------------------------
# INSTALLED APPS
# -----------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",           # Django REST Framework
    "corsheaders",              # Allow React frontend to call API
    "backend.api",              # Our violation API app
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",   # must be FIRST
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "backend.wsgi.application"

# -----------------------------------------------------------------------------
# DATABASE — SQLite for development (easy, no installation needed)
# Switch to PostgreSQL for production by changing the ENGINE below
# -----------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME"  : BASE_DIR / "db.sqlite3",

        # ── PostgreSQL (uncomment when ready for production) ──────────────────
        # "ENGINE"  : "django.db.backends.postgresql",
        # "NAME"    : os.getenv("DB_NAME",     "traffic_db"),
        # "USER"    : os.getenv("DB_USER",     "postgres"),
        # "PASSWORD": os.getenv("DB_PASSWORD", "your_password"),
        # "HOST"    : os.getenv("DB_HOST",     "localhost"),
        # "PORT"    : os.getenv("DB_PORT",     "5432"),
    }
}

# -----------------------------------------------------------------------------
# REST FRAMEWORK SETTINGS
# -----------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",  # nice web UI
    ],
    "DEFAULT_PAGINATION_CLASS" : "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE"                : 20,
}

# -----------------------------------------------------------------------------
# CORS — allow React frontend (localhost:3000) to call the API
# -----------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ALLOW_ALL_ORIGINS = True   # set False in production

# -----------------------------------------------------------------------------
# MEDIA FILES — violation images uploaded/saved here
# -----------------------------------------------------------------------------

MEDIA_URL  = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STATIC_URL = "/static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "en-us"
TIME_ZONE     = "Asia/Kolkata"
USE_I18N      = True
USE_TZ        = True
CELERY_BROKER_URL         = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND     = "redis://localhost:6379/0"
CELERY_ACCEPT_CONTENT     = ["json"]
CELERY_TASK_SERIALIZER    = "json"
CELERY_RESULT_SERIALIZER  = "json"
CELERY_TIMEZONE           = "Asia/Kolkata"
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True