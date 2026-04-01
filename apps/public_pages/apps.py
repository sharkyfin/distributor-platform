from __future__ import annotations

from django.apps import AppConfig


class PublicPagesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.public_pages"
    verbose_name = "Публичные страницы"

