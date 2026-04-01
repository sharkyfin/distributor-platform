from __future__ import annotations

from . import base as base_settings
from .base import *  # noqa: F403,F401

DEBUG = base_settings.env.bool("DEBUG", default=True)
SECRET_KEY = base_settings.env("DJANGO_SECRET_KEY", default="local-development-secret-key")
EMAIL_BACKEND = base_settings.env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)

TEMPLATES = base_settings.TEMPLATES
TEMPLATES[0]["OPTIONS"]["debug"] = DEBUG
