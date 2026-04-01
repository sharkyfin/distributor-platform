from __future__ import annotations

from pathlib import Path

import environ
from celery.schedules import crontab
from django.templatetags.static import static

from apps.core.storage import build_storage_settings

BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env.bool("DEBUG", default=False)
SECRET_KEY = env("DJANGO_SECRET_KEY", default="change-me")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

DJANGO_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "django_htmx",
    "phonenumber_field",
    "storages",
]

LOCAL_APPS = [
    "apps.core.apps.CoreConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.organizations.apps.OrganizationsConfig",
    "apps.branches.apps.BranchesConfig",
    "apps.dealers.apps.DealersConfig",
    "apps.machines.apps.MachinesConfig",
    "apps.warranties.apps.WarrantiesConfig",
    "apps.service.apps.ServiceConfig",
    "apps.attachments.apps.AttachmentsConfig",
    "apps.public_pages.apps.PublicPagesConfig",
    "apps.auditlog.apps.AuditlogConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

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

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://platform:platform@localhost:5432/platform",
    )
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE", default=60)

REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

if cache_url := env("CACHE_URL", default=""):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": cache_url,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "service-platform",
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]

LANGUAGE_CODE = "ru"
LANGUAGES = [
    ("ru", "Русский"),
    ("en", "English"),
]
TIME_ZONE = env("TIME_ZONE", default="Europe/Moscow")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = build_storage_settings(env)

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.local")
SERVER_EMAIL = env("SERVER_EMAIL", default="server@example.local")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=1025)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
EMAIL_TIMEOUT = 10

LOGIN_URL = "admin:login"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
APPEND_SLASH = True
PUBLIC_CONTACT_EMAIL = env(
    "PUBLIC_CONTACT_EMAIL",
    default="service@atlas-machinery.ru",
)
PUBLIC_CONTACT_PHONE = env(
    "PUBLIC_CONTACT_PHONE",
    default="",
)
PUBLIC_OPERATOR_NAME = env(
    "PUBLIC_OPERATOR_NAME",
    default="Сервисная служба",
)
PUBLIC_OPERATOR_ADDRESS = env("PUBLIC_OPERATOR_ADDRESS", default="Москва, Россия")

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_PERMISSIONS = 0o640

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

PHONENUMBER_DEFAULT_REGION = "RU"
PHONENUMBER_DB_FORMAT = "E164"

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env(
    "CELERY_RESULT_BACKEND",
    default="redis://localhost:6379/2",
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_IMPORTS = (
    "apps.core.tasks",
    "apps.machines.tasks",
    "apps.warranties.tasks",
)
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_IGNORE_RESULT = env.bool("CELERY_TASK_IGNORE_RESULT", default=True)
CELERY_TASK_SOFT_TIME_LIMIT = env.int("CELERY_TASK_SOFT_TIME_LIMIT", default=240)
CELERY_TASK_TIME_LIMIT = env.int("CELERY_TASK_TIME_LIMIT", default=300)
CELERY_WORKER_CONCURRENCY = env.int("CELERY_WORKER_CONCURRENCY", default=2)
CELERY_BEAT_SCHEDULE = {
    "sync-warranty-statuses-nightly": {
        "task": "apps.warranties.tasks.sync_warranty_statuses",
        "schedule": crontab(hour=2, minute=10),
    },
    "refresh-machine-maintenance-snapshots-hourly": {
        "task": "apps.machines.tasks.refresh_machine_maintenance_snapshots",
        "schedule": crontab(minute=20),
    },
}

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_RENDERER_CLASSES": (
        [
            "rest_framework.renderers.JSONRenderer",
            "rest_framework.renderers.BrowsableAPIRenderer",
        ]
        if DEBUG
        else ["rest_framework.renderers.JSONRenderer"]
    ),
}

UNFOLD = {
    "SITE_TITLE": "Цифровой сервисный паспорт",
    "SITE_HEADER": "Сервисный паспорт",
    "SITE_SUBHEADER": "Платформа поддержки спецтехники",
    "SITE_URL": "/",
    "SITE_SYMBOL": "precision_manufacturing",
    "SITE_ICON": lambda request: static("brand/icon.svg"),
    "SITE_LOGO": {
        "light": lambda request: static("brand/logo-light.svg"),
        "dark": lambda request: static("brand/logo-dark.svg"),
    },
    "STYLES": [
        lambda request: static("admin/custom_admin.css"),
    ],
    "DASHBOARD_CALLBACK": "apps.core.admin.admin_dashboard_callback",
    "ENVIRONMENT": "apps.core.admin.admin_environment_badge",
    "ACCOUNT": {
        "navigation": [
            {
                "title": "Публичный сайт",
                "link": "/",
            },
            {
                "title": "Контакты",
                "link": "/contact/",
            },
        ]
    },
    "SIDEBAR": {
        "show_search": True,
        "command_search": True,
        "show_all_applications": False,
        "navigation": "apps.core.admin.admin_sidebar_navigation",
    },
    "COLORS": {
        "base": {
            "50": "#f6f7f7",
            "100": "#eceff0",
            "200": "#dce1e4",
            "300": "#c4cdd3",
            "400": "#8e9ca6",
            "500": "#66757f",
            "600": "#4f5d66",
            "700": "#3a454d",
            "800": "#232b31",
            "900": "#171d22",
            "950": "#0f1418",
        },
        "primary": {
            "50": "#fbf6f1",
            "100": "#f5e7d7",
            "200": "#ecd0b0",
            "300": "#dfb27e",
            "400": "#cf9053",
            "500": "#b87135",
            "600": "#995924",
            "700": "#7a471d",
            "800": "#603719",
            "900": "#4c2d16",
            "950": "#2d190a",
        },
        "font": {
            "subtle-light": "#66757f",
            "subtle-dark": "#8e9ca6",
            "default-light": "#4f5d66",
            "default-dark": "#c4cdd3",
            "important-light": "#171d22",
            "important-dark": "#f6f7f7",
        },
    },
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": env("LOG_LEVEL", default="INFO"),
    },
}
