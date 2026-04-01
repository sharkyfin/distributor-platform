from __future__ import annotations

from pathlib import Path
from tempfile import gettempdir

from . import base as base_settings
from .base import *  # noqa: F403,F401

DEBUG = False
SECRET_KEY = "test-secret-key"

TEST_DIR = Path(gettempdir()) / "service-passport-tests"
TEST_DIR.mkdir(parents=True, exist_ok=True)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": TEST_DIR / "db.sqlite3",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "service-passport-tests",
    }
}

MEDIA_ROOT = TEST_DIR / "media"
STATIC_ROOT = TEST_DIR / "staticfiles"
STATIC_ROOT.mkdir(parents=True, exist_ok=True)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": MEDIA_ROOT,
            "base_url": MEDIA_URL,  # noqa: F405
        },
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_IGNORE_RESULT = False
CELERY_RESULT_BACKEND = "cache+memory://"
CELERY_BROKER_URL = "memory://"

TEMPLATES = base_settings.TEMPLATES
TEMPLATES[0]["OPTIONS"]["debug"] = False
