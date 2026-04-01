from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from apps.core.models import OrganizationScopedModel


class Region(OrganizationScopedModel):
    name = models.CharField(_("Название региона"), max_length=255)
    code = models.CharField(_("Код региона"), max_length=32)
    ordering = models.PositiveSmallIntegerField(_("Порядок"), default=100)
    is_active = models.BooleanField(_("Активен"), default=True, db_index=True)

    class Meta:
        verbose_name = "Регион"
        verbose_name_plural = "Регионы"
        ordering = ("organization__name", "ordering", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                condition=models.Q(is_deleted=False),
                name="uniq_region_code_per_org_active",
            )
        ]

    def __str__(self) -> str:
        return self.name


class Branch(OrganizationScopedModel):
    name = models.CharField(_("Название филиала"), max_length=255)
    code = models.CharField(_("Код филиала"), max_length=32)
    region = models.ForeignKey(
        "branches.Region",
        on_delete=models.PROTECT,
        related_name="branches",
        verbose_name=_("Регион"),
    )
    address = models.TextField(_("Адрес"), blank=True)
    phone = PhoneNumberField(_("Основной телефон"), blank=True)
    emergency_phone = PhoneNumberField(_("Экстренный телефон"), blank=True)
    service_phone = PhoneNumberField(_("Телефон сервиса"), blank=True)
    service_email = models.EmailField(_("Email сервиса"), blank=True)
    service_contact_info = models.TextField(_("Информация для сервиса"), blank=True)
    is_active = models.BooleanField(_("Активен"), default=True, db_index=True)

    class Meta:
        verbose_name = "Филиал"
        verbose_name_plural = "Филиалы"
        ordering = ("organization__name", "region__ordering", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                condition=models.Q(is_deleted=False),
                name="uniq_branch_code_per_org_active",
            )
        ]

    def __str__(self) -> str:
        return self.name

    def clean(self):
        super().clean()
        if self.region_id and self.region.organization_id != self.organization_id:
            raise ValidationError(_("Регион филиала должен принадлежать той же организации."))

