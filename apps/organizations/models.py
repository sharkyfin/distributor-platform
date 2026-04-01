from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from apps.core.models import SoftDeleteModel


class Organization(SoftDeleteModel):
    name = models.CharField(_("Название"), max_length=255)
    code = models.SlugField(_("Код"), max_length=64, unique=True)
    legal_name = models.CharField(_("Юридическое название"), max_length=255, blank=True)
    inn = models.CharField(_("ИНН"), max_length=12, blank=True)
    phone = PhoneNumberField(_("Телефон"), blank=True)
    email = models.EmailField(_("Email"), blank=True)
    website = models.URLField(_("Сайт"), blank=True)
    address = models.TextField(_("Адрес"), blank=True)
    is_active = models.BooleanField(_("Активна"), default=True, db_index=True)

    class Meta:
        verbose_name = "Организация"
        verbose_name_plural = "Организации"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

