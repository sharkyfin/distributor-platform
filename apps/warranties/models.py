from __future__ import annotations

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import OrganizationScopedModel


class WarrantyTypeChoices(models.TextChoices):
    STANDARD = "standard", _("Стандартная")
    EXTENDED = "extended", _("Расширенная")
    POWERTRAIN = "powertrain", _("Силовая линия")
    SERVICE_CONTRACT = "service_contract", _("Сервисный контракт")
    OTHER = "other", _("Другое")


class WarrantyStatusChoices(models.TextChoices):
    ACTIVE = "active", _("Действует")
    EXPIRING = "expiring", _("Истекает")
    EXPIRED = "expired", _("Истекла")
    VOID = "void", _("Аннулирована")
    PENDING = "pending", _("Ожидает начала")


class Warranty(OrganizationScopedModel):
    machine = models.ForeignKey(
        "machines.Machine",
        on_delete=models.PROTECT,
        related_name="warranties",
        verbose_name=_("Машина"),
    )
    warranty_start = models.DateField(_("Начало гарантии"))
    warranty_end = models.DateField(_("Окончание гарантии"))
    warranty_type = models.CharField(
        _("Тип гарантии"),
        max_length=24,
        choices=WarrantyTypeChoices.choices,
        default=WarrantyTypeChoices.STANDARD,
    )
    status = models.CharField(
        _("Статус"),
        max_length=16,
        choices=WarrantyStatusChoices.choices,
        default=WarrantyStatusChoices.PENDING,
        db_index=True,
    )
    public_summary = models.CharField(_("Публичное описание"), max_length=255, blank=True)
    notes = models.TextField(_("Внутренние заметки"), blank=True)

    class Meta:
        verbose_name = "Гарантия"
        verbose_name_plural = "Гарантии"
        ordering = ("-warranty_end",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(warranty_end__gte=models.F("warranty_start")),
                name="warranty_end_after_start",
            )
        ]

    def __str__(self) -> str:
        return f"{self.machine} / {self.get_warranty_type_display()}"

    def clean(self):
        super().clean()
        if self.machine_id and not self.organization_id:
            self.organization_id = self.machine.organization_id
        if self.machine_id and self.machine.organization_id != self.organization_id:
            raise ValidationError(
                _("Гарантия должна принадлежать той же организации, что и машина.")
            )
        if self.warranty_end < self.warranty_start:
            raise ValidationError(_("Дата окончания гарантии не может быть раньше даты начала."))

    def save(self, *args, **kwargs):
        if self.machine_id:
            self.organization_id = self.machine.organization_id

        today = timezone.localdate()
        if self.status != WarrantyStatusChoices.VOID:
            if today < self.warranty_start:
                self.status = WarrantyStatusChoices.PENDING
            elif today > self.warranty_end:
                self.status = WarrantyStatusChoices.EXPIRED
            elif self.warranty_end <= today + timedelta(days=30):
                self.status = WarrantyStatusChoices.EXPIRING
            else:
                self.status = WarrantyStatusChoices.ACTIVE

        super().save(*args, **kwargs)
