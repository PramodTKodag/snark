"""
Django settings for snark — AI-Powered Humor & Utility API.

Public service with IP-based rate limiting only. No authentication required.
"""

from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1,wit.snark.test,snark",
    cast=lambda v: [h.strip() for h in v.split(",")],
)

# NOTE: django.contrib.auth/sessions/messages are retained intentionally — they
# are required by the Django admin, which operators use to manage Persona rows.
# The public API itself uses no authentication (DEFAULT_AUTHENTICATION_CLASSES=[]).
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "base",
    "wit",
    "rest_framework",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "corsheaders",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

APPEND_SLASH = True

ROOT_URLCONF = "base.urls"

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # No default throttle — BaseWitView applies WitAnonThrottle explicitly.
    # This keeps Swagger/schema/health views unthrottled.
    "DEFAULT_THROTTLE_RATES": {
        "anon": "50/hour",
    },
}

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

WSGI_APPLICATION = "base.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": config("POSTGRES_DB", default="snark"),
        "USER": config("POSTGRES_USER", default="postgres"),
        "PASSWORD": config("POSTGRES_PASSWORD"),
        "HOST": config("POSTGRES_HOST", default="localhost"),
        "PORT": config("POSTGRES_PORT", default=5432, cast=int),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/v1/wit/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Production security hardening
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Redis Configuration
REDIS_HOST = config("REDIS_HOST", default="localhost")
REDIS_PORT = config("REDIS_PORT", default=6379, cast=int)
REDIS_DB = config("REDIS_DB", default=9, cast=int)
REDIS_PASSWORD = config("REDIS_PASSWORD", default=None)

if REDIS_PASSWORD:
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
                "retry_on_timeout": True,
            },
        },
        "KEY_PREFIX": "snark",
        "TIMEOUT": 300,
    },
}

# AI Provider Configuration — settings are the single source of truth.
AI_DEFAULT_PROVIDER = config("AI_DEFAULT_PROVIDER", default="groq")
AI_PROVIDER_FALLBACK_ORDER = config(
    "AI_PROVIDER_FALLBACK_ORDER",
    default="groq,gemini,claude",
    cast=lambda v: [p.strip() for p in v.split(",") if p.strip()],
)
AI_DEFAULT_MAX_TOKENS = config("AI_DEFAULT_MAX_TOKENS", default=300, cast=int)

# Per-provider model identifiers (real model ids; override via env per deployment).
GROQ_MODEL = config("GROQ_MODEL", default="llama-3.3-70b-versatile")
GEMINI_MODEL = config("GEMINI_MODEL", default="gemini-2.0-flash")
CLAUDE_MODEL = config("CLAUDE_MODEL", default="claude-haiku-4-5-20251001")

# Per-provider API key env var names.
GROQ_API_KEY_ENV_VAR = config("GROQ_API_KEY_ENV_VAR", default="GROQ_API_KEY")
GEMINI_API_KEY_ENV_VAR = config("GEMINI_API_KEY_ENV_VAR", default="GEMINI_API_KEY")
ANTHROPIC_API_KEY_ENV_VAR = config(
    "ANTHROPIC_API_KEY_ENV_VAR", default="ANTHROPIC_API_KEY"
)

# drf-spectacular settings
SPECTACULAR_SETTINGS = {
    "TITLE": "Snark API",
    "DESCRIPTION": "AI-Powered Humor & Utility API — every response uniquely generated.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
    "SERVERS": [],
    "SCHEMA_PATH_PREFIX": "/v1/wit/",
    "TAGS": [
        {"name": "Wit", "description": "AI-powered humor endpoints"},
        {"name": "Health", "description": "Service health probes"},
    ],
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "docExpansion": "list",
        "tryItOutEnabled": True,
    },
}

# CORS — public, read-only, no-credential API. Allow all origins by default;
# restrict per deployment by setting CORS_ALLOW_ALL_ORIGINS=False and listing
# CORS_ALLOWED_ORIGINS.
CORS_ALLOW_ALL_ORIGINS = config("CORS_ALLOW_ALL_ORIGINS", default=True, cast=bool)
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="",
    cast=lambda v: [o.strip() for o in v.split(",") if o.strip()],
)
CORS_ALLOW_CREDENTIALS = False
