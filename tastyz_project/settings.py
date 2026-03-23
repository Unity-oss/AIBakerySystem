"""
Django settings for Tastyz Bakery AI System.
"""

import logging
import os
from pathlib import Path

import environ

# ============================================================
# Base directory
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================
# Environment variables
# ============================================================
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
)
environ.Env.read_env(BASE_DIR / ".env")

# ============================================================
# Core Django settings
# ============================================================
SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-key-change-in-production")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS", default="localhost,127.0.0.1").split(",")

# CSRF & Security
CSRF_TRUSTED_ORIGINS = env(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:8000"
).split(",")

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# ============================================================
# Installed apps
# ============================================================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "bakery",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "tastyz_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "tastyz_project.wsgi.application"

# ============================================================
# Database
# ============================================================
# PostgreSQL for production (Railway), SQLite for local dev
if env("DATABASE_URL", default=None):
    import dj_database_url
    DATABASES = {
        "default": dj_database_url.config(
            default=env("DATABASE_URL"),
            conn_max_age=600,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ============================================================
# Static files
# ============================================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = []
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ============================================================
# Internationalization
# ============================================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Kampala"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ============================================================
# AI / LLM Settings
# ============================================================
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
OPENAI_MODEL = env("OPENAI_MODEL", default="gpt-4o-mini")
OPENAI_EMBEDDING_MODEL = env("OPENAI_EMBEDDING_MODEL", default="text-embedding-3-small")

# Google Gemini
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
GEMINI_MODEL = env("GEMINI_MODEL", default="gemini-pro")

# Anthropic Claude
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")

# ChromaDB
CHROMA_PERSIST_DIR = env("CHROMA_PERSIST_DIR", default=str(BASE_DIR / "chroma_db"))

# Knowledge base sources
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"

# Excel orders export
ORDERS_EXCEL_PATH = BASE_DIR / "orders.xlsx"

# ============================================================
# LangSmith (monitoring / observability)
# ============================================================
LANGSMITH_API_KEY = env("LANGSMITH_API_KEY", default="")

# ============================================================
# Grok (xAI)
# ============================================================
GROK_API_KEY = env("GROK_API_KEY", default="")
GROK_MODEL = env("GROK_MODEL", default="grok-2")

# ============================================================
# Ollama (Local LLM)
# ============================================================
OLLAMA_BASE_URL = env("OLLAMA_BASE_URL", default="http://localhost:11434")
OLLAMA_MODEL = env("OLLAMA_MODEL", default="mistral")

# ============================================================
# Pinecone (Vector Search)
# ============================================================
PINECONE_API_KEY = env("PINECONE_API_KEY", default="")
PINECONE_ENVIRONMENT = env("PINECONE_ENVIRONMENT", default="")

# ============================================================
# Google Calendar
# ============================================================
GOOGLE_CALENDAR_CLIENT_ID = env("GOOGLE_CALENDAR_CLIENT_ID", default="")
GOOGLE_CALENDAR_CLIENT_SECRET = env("GOOGLE_CALENDAR_CLIENT_SECRET", default="")

# ============================================================
# Payment Gateways
# ============================================================
# Stripe — .env uses STRIPE_API_KEY
STRIPE_SECRET_KEY = env("STRIPE_API_KEY", default="")
STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY", default="")

# Flutterwave — .env uses FLUTTERWAVE_PUBLIC_KEY / SECRET_KEY / ENCRYPTION_KEY
FLUTTERWAVE_PUBLIC_KEY = env("FLUTTERWAVE_PUBLIC_KEY", default="")
FLUTTERWAVE_SECRET_KEY = env("FLUTTERWAVE_SECRET_KEY", default="")
FLUTTERWAVE_ENCRYPTION_KEY = env("FLUTTERWAVE_ENCRYPTION_KEY", default="")

# ============================================================
# Celery (background task queue)
# ============================================================
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Africa/Kampala"

# Celery beat schedule
from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    "daily-sales-report": {
        "task": "bakery.tasks.run_daily_sales_report",
        "schedule": crontab(hour=20, minute=0),  # 8 PM daily
    },
}

# ============================================================
# Email (optional, for sending reports)
# ============================================================
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
BAKER_EMAIL = env("BAKER_EMAIL", default="baker@tastyzbakery.com")

# ============================================================
# Logging — JSON structured logs
# ============================================================
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        },
        "verbose": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "tastyz.log",
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "bakery": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "agents": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
