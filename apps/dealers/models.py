from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from apps.core.models import OrganizationScopedModel


class Dealer(OrganizationScopedModel):
    name = models.CharField(_("Название дилера"), max_length=255)
    code = models.CharField(_("Код дилера"), max_length=32)
    legal_name = models.CharField(_("Юридическое название"), max_length=255, blank=True)
    address = models.TextField(_("Адрес"), blank=True)
    phone = PhoneNumberField(_("Телефон"), blank=True)
    emergency_phone = PhoneNumberField(_("Экстренный телефон"), blank=True)
    email = models.EmailField(_("Email"), blank=True)
    website = models.URLField(_("Сайт"), blank=True)
    is_active = models.BooleanField(_("Активен"), default=True, db_index=True)
    branches = models.ManyToManyField(
        "branches.Branch",
        related_name="dealers",
        verbose_name=_("Филиалы"),
        blank=True,
    )

    class Meta:
        verbose_name = "Дилер"
        verbose_name_plural = "Дилеры"
        ordering = ("organization__name", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                condition=models.Q(is_deleted=False),
                name="uniq_dealer_code_per_org_active",
            )
        ]

    def __str__(self) -> str:
        return self.name


class ContactVisibilityChoices(models.TextChoices):
    PUBLIC = "public", _("Публичный")
    INTERNAL = "internal", _("Внутренний")


class ContactTypeChoices(models.TextChoices):
    SERVICE = "service", _("Сервис")
    EMERGENCY = "emergency", _("Экстренный")
    MANAGER = "manager", _("Менеджер")
    SALES = "sales", _("Продажи")
    OPERATOR = "operator", _("Оператор")
    OTHER = "other", _("Другое")


class Contact(OrganizationScopedModel):
    dealer = models.ForeignKey(
        "dealers.Dealer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contacts",
        verbose_name=_("Дилер"),
    )
    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contacts",
        verbose_name=_("Филиал"),
    )
    full_name = models.CharField(_("ФИО"), max_length=255)
    title = models.CharField(_("Должность"), max_length=255, blank=True)
    phone = PhoneNumberField(_("Телефон"), blank=True)
    email = models.EmailField(_("Email"), blank=True)
    contact_type = models.CharField(
        _("Тип контакта"),
        max_length=24,
        choices=ContactTypeChoices.choices,
        default=ContactTypeChoices.SERVICE,
    )
    visibility = models.CharField(
        _("Видимость"),
        max_length=16,
        choices=ContactVisibilityChoices.choices,
        default=ContactVisibilityChoices.INTERNAL,
    )
    public_note = models.CharField(_("Публичная заметка"), max_length=255, blank=True)
    private_note = models.TextField(_("Внутренняя заметка"), blank=True)
    is_primary = models.BooleanField(_("Основной контакт"), default=False)

    class Meta:
        verbose_name = "Контакт"
        verbose_name_plural = "Контакты"
        ordering = ("organization__name", "full_name")

    def __str__(self) -> str:
        return self.full_name

    def clean(self):
        super().clean()
        if self.dealer_id and self.dealer.organization_id != self.organization_id:
            raise ValidationError(_("Дилер контакта должен принадлежать выбранной организации."))
        if self.branch_id and self.branch.organization_id != self.organization_id:
            raise ValidationError(_("Филиал контакта должен принадлежать выбранной организации."))

