from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class AuditActionChoices(models.TextChoices):
    CREATED = "created", _("Создание")
    UPDATED = "updated", _("Изменение")
    DELETED = "deleted", _("Удаление")
    STATUS_CHANGED = "status_changed", _("Смена статуса")
    ASSIGNED = "assigned", _("Назначение")
    LOGIN = "login", _("Вход")
    PUBLIC_REQUEST_CREATED = "public_request_created", _("Создание публичной заявки")
    EXPORT = "export", _("Экспорт")


class AuditLog(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name=_("Организация"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name=_("Пользователь"),
    )
    action = models.CharField(
        _("Действие"),
        max_length=32,
        choices=AuditActionChoices.choices,
        db_index=True,
    )
    model_name = models.CharField(_("Модель"), max_length=128, db_index=True)
    object_id = models.CharField(_("ID объекта"), max_length=64, db_index=True)
    object_repr = models.CharField(_("Представление объекта"), max_length=255, blank=True)
    summary = models.CharField(_("Краткое описание"), max_length=255)
    payload = models.JSONField(_("Дополнительные данные"), default=dict, blank=True)
    timestamp = models.DateTimeField(_("Время"), default=timezone.now, db_index=True)

    class Meta:
        verbose_name = "Запись аудита"
        verbose_name_plural = "Журнал аудита"
        ordering = ("-timestamp",)

    def __str__(self) -> str:
        return self.summary
