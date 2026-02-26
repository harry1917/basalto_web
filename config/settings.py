from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# =========================
# Core
# =========================
DEBUG = os.getenv("DEBUG", "False").lower() in ("1", "true", "yes")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-change-me")

ALLOWED_HOSTS = [
    h.strip() for h in os.getenv(
        "ALLOWED_HOSTS",
        "127.0.0.1,localhost"
    ).split(",") if h.strip()
]

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.getenv(
        "CSRF_TRUSTED_ORIGINS",
        "http://127.0.0.1,http://localhost,http://127.0.0.1:8000,http://localhost:8000"
    ).split(",") if o.strip()
]


# =========================
# Frontend / Backend URLs
# =========================
# 👉 FRONTEND = web pública (basalto1530.com)
# 👉 BACKEND = Railway (para webhooks)
FRONTEND_DOMAIN = os.getenv("FRONTEND_DOMAIN", "http://127.0.0.1:8000").rstrip("/")
BACKEND_DOMAIN = os.getenv("BACKEND_DOMAIN", FRONTEND_DOMAIN).rstrip("/")

WOMPI_WEBHOOK_URL = f"{BACKEND_DOMAIN}/wompi/callback/"

# =========================
# Auth URLs
# =========================
LOGIN_URL = "/dashboard/login/"
LOGIN_REDIRECT_URL = "/dashboard/orders/"
LOGOUT_REDIRECT_URL = "/dashboard/login/"

# =========================
# Apps
# =========================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "orders",
]

# =========================
# Middleware
# =========================
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

ROOT_URLCONF = "config.urls"

# =========================
# Templates
# =========================
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
                "config.context_processors.cdn",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# =========================
# Database
# =========================
DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
    )
}

# =========================
# Internationalization
# =========================
LANGUAGE_CODE = "es"
TIME_ZONE = "America/El_Salvador"
USE_I18N = True
USE_TZ = True

# =========================
# Static files
# =========================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
CDN_BASE_URL = os.getenv("CDN_BASE_URL", "")


# ✅ para desarrollo: tus assets viven en /static


STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
WHITENOISE_MANIFEST_STRICT = False


# =========================
# Wompi SV
# =========================
WOMPI_CLIENT_ID = os.getenv("WOMPI_CLIENT_ID", "")
WOMPI_CLIENT_SECRET = os.getenv("WOMPI_CLIENT_SECRET", "")
WOMPI_AUDIENCE = os.getenv("WOMPI_AUDIENCE", "wompi_api")

WOMPI_TOKEN_URL = os.getenv(
    "WOMPI_TOKEN_URL",
    "https://id.wompi.sv/connect/token"
)

WOMPI_API_BASE = os.getenv(
    "WOMPI_API_BASE",
    "https://api.wompi.sv"
)

# =========================
# WhatsApp
# =========================
BASALTO_WHATSAPP_NUMBER = os.getenv("BASALTO_WHATSAPP_NUMBER", "50378455804")
