from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import OrganizationScopedModel
from apps.core.utils import build_upload_path


def attachment_upload_to(instance, filename: str) -> str:
    return build_upload_path(f"attachments/{instance.organization_id}", filename)


class AttachmentFileTypeChoices(models.TextChoices):
    IMAGE = "image", _("Изображение")
    PDF = "pdf", _("PDF")
    DOCUMENT = "document", _("Документ")
    SPREADSHEET = "spreadsheet", _("Таблица")
    ARCHIVE = "archive", _("Архив")
    OTHER = "other", _("Другое")


class AttachmentVisibilityChoices(models.TextChoices):
    PUBLIC = "public", _("Публичный")
    INTERNAL = "internal", _("Внутренний")


class Attachment(OrganizationScopedModel):
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Тип объекта"),
    )
    object_id = models.PositiveBigIntegerField(_("ID объекта"))
    content_object = GenericForeignKey("content_type", "object_id")
    title = models.CharField(_("Название"), max_length=255, blank=True)
    file = models.FileField(_("Файл"), upload_to=attachment_upload_to)
    file_type = models.CharField(
        _("Тип файла"),
        max_length=16,
        choices=AttachmentFileTypeChoices.choices,
        default=AttachmentFileTypeChoices.OTHER,
    )
    visibility = models.CharField(
        _("Видимость"),
        max_length=16,
        choices=AttachmentVisibilityChoices.choices,
        default=AttachmentVisibilityChoices.INTERNAL,
        db_index=True,
    )
    original_name = models.CharField(_("Оригинальное имя файла"), max_length=255, blank=True)
    mime_type = models.CharField(_("MIME-тип"), max_length=128, blank=True)
    size = models.PositiveBigIntegerField(_("Размер, байт"), default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attachments",
        verbose_name=_("Загрузил"),
    )

    class Meta:
        verbose_name = "Вложение"
        verbose_name_plural = "Вложения"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["organization", "visibility"]),
        ]

    def __str__(self) -> str:
        return self.title or self.original_name or self.file.name

    def save(self, *args, **kwargs):
        if self.file and not self.original_name:
            self.original_name = self.file.name.rsplit("/", 1)[-1]
        if self.file and not self.size:
            self.size = self.file.size

        if not self.organization_id and self.content_object is not None:
            organization_id = getattr(self.content_object, "organization_id", None)
            if organization_id:
                self.organization_id = organization_id

        super().save(*args, **kwargs)

