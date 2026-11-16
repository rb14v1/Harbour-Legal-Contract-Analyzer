"""
Django settings for the Legal Contract Analyzer backend.
"""
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="django-insecure-dev-only")
DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# --- Toggle: SQLite + fully-stubbed Azure services (dev/test/CI) vs real Postgres ---
USE_SQLITE = config("USE_SQLITE", default=True, cast=bool)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "apps.users",
    "apps.contracts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"

# --- Database ---
if USE_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("POSTGRES_DB", default="legal_contract_analyzer"),
            "USER": config("POSTGRES_USER", default="legal_contract_analyzer"),
            "PASSWORD": config("POSTGRES_PASSWORD", default="legal_contract_analyzer"),
            "HOST": config("POSTGRES_HOST", default="localhost"),
            "PORT": config("POSTGRES_PORT", default="5432"),
        }
    }

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF / JWT ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=config("ACCESS_TOKEN_LIFETIME_MINUTES", default=60, cast=int)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=config("REFRESH_TOKEN_LIFETIME_DAYS", default=7, cast=int)),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# --- CORS ---
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS", default="http://localhost:5173", cast=Csv()
)

# --- Azure / AI integration settings (read once here, used by apps/common/*.py) ---
AZURE_STORAGE_CONNECTION_STRING = config("AZURE_STORAGE_CONNECTION_STRING", default="")

AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = config("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", default="")
AZURE_DOCUMENT_INTELLIGENCE_KEY = config("AZURE_DOCUMENT_INTELLIGENCE_KEY", default="")

AZURE_OPENAI_ENDPOINT = config("AZURE_OPENAI_ENDPOINT", default="")
AZURE_OPENAI_API_KEY = config("AZURE_OPENAI_API_KEY", default="")
AZURE_OPENAI_API_VERSION = config("AZURE_OPENAI_API_VERSION", default="2024-10-21")
OPENAI_CHAT_MODEL = config("OPENAI_CHAT_MODEL", default="gpt-5.6-sol")
OPENAI_EMBEDDING_MODEL = config("OPENAI_EMBEDDING_MODEL", default="text-embedding-3-large")
EMBEDDING_DIMENSIONS = config("EMBEDDING_DIMENSIONS", default=1536, cast=int)

AZURE_SEARCH_ENDPOINT = config("AZURE_SEARCH_ENDPOINT", default="")
AZURE_SEARCH_KEY = config("AZURE_SEARCH_KEY", default="")
AZURE_SEARCH_INDEX = config("AZURE_SEARCH_INDEX", default="contract_chunks")
