from __future__ import annotations

from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from apps.core.models import OrganizationScopedModel
from apps.core.utils import build_upload_path, generate_public_token


def machine_photo_upload_to(instance, filename: str) -> str:
    return build_upload_path(f"machines/{instance.organization_id}/photos", filename)


class MachineCategoryChoices(models.TextChoices):
    EXCAVATOR = "excavator", _("Экскаватор")
    LOADER = "loader", _("Погрузчик")
    CRANE = "crane", _("Кран")
    DOZER = "dozer", _("Бульдозер")
    GRADER = "grader", _("Автогрейдер")
    OTHER = "other", _("Другое")


class MachineStatusChoices(models.TextChoices):
    ACTIVE = "active", _("В эксплуатации")
    SERVICE = "service", _("На сервисе")
    INACTIVE = "inactive", _("Неактивна")
    DECOMMISSIONED = "decommissioned", _("Выведена из эксплуатации")


class Machine(OrganizationScopedModel):
    name = models.CharField(_("Название машины"), max_length=255)
    model_name = models.CharField(_("Модель"), max_length=255)
    serial_number = models.CharField(_("Серийный номер"), max_length=128)
    inventory_number = models.CharField(_("Инвентарный номер"), max_length=64, blank=True)
    category = models.CharField(
        _("Категория"),
        max_length=24,
        choices=MachineCategoryChoices.choices,
        default=MachineCategoryChoices.OTHER,
    )
    status = models.CharField(
        _("Статус"),
        max_length=24,
        choices=MachineStatusChoices.choices,
        default=MachineStatusChoices.ACTIVE,
        db_index=True,
    )
    photo = models.ImageField(_("Фото"), upload_to=machine_photo_upload_to, blank=True)
    description = models.TextField(_("Описание"), blank=True)
    dealer = models.ForeignKey(
        "dealers.Dealer",
        on_delete=models.PROTECT,
        related_name="machines",
        verbose_name=_("Дилер"),
        null=True,
        blank=True,
    )
    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.PROTECT,
        related_name="machines",
        verbose_name=_("Филиал"),
    )
    region = models.ForeignKey(
        "branches.Region",
        on_delete=models.PROTECT,
        related_name="machines",
        verbose_name=_("Регион"),
    )
    emergency_phone = PhoneNumberField(_("Экстренный телефон"), blank=True)
    is_active = models.BooleanField(_("Активна"), default=True, db_index=True)
    is_public = models.BooleanField(_("Публично доступна"), default=True, db_index=True)
    commissioning_date = models.DateField(_("Дата ввода в эксплуатацию"), null=True, blank=True)
    operating_hours = models.PositiveIntegerField(
        _("Наработка, моточасы"),
        null=True,
        blank=True,
    )
    last_maintenance_date = models.DateField(
        _("Дата последнего обслуживания"),
        null=True,
        blank=True,
    )
    next_maintenance_date = models.DateField(
        _("Дата следующего обслуживания"),
        null=True,
        blank=True,
    )
    attachments = GenericRelation(
        "attachments.Attachment",
        related_query_name="machine",
        verbose_name=_("Вложения"),
    )

    class Meta:
        verbose_name = "Машина"
        verbose_name_plural = "Машины"
        ordering = ("organization__name", "name", "serial_number")
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "serial_number"],
                condition=models.Q(is_deleted=False),
                name="uniq_machine_serial_per_org_active",
            ),
            models.UniqueConstraint(
                fields=["organization", "inventory_number"],
                condition=models.Q(is_deleted=False) & ~models.Q(inventory_number=""),
                name="uniq_machine_inventory_per_org_active",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "next_maintenance_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.serial_number})"

    def clean(self):
        super().clean()
        if self.branch_id and self.branch.organization_id != self.organization_id:
            raise ValidationError(_("Филиал машины должен принадлежать выбранной организации."))
        if self.region_id and self.region.organization_id != self.organization_id:
            raise ValidationError(_("Регион машины должен принадлежать выбранной организации."))
        if self.dealer_id and self.dealer.organization_id != self.organization_id:
            raise ValidationError(_("Дилер машины должен принадлежать выбранной организации."))
        if self.branch_id and self.region_id and self.branch.region_id != self.region_id:
            raise ValidationError(_("Филиал машины должен принадлежать выбранному региону."))

    @property
    def active_tag(self):
        return self.tags.filter(is_active=True, is_deleted=False).first()

    @property
    def current_warranty(self):
        today = timezone.localdate()
        return (
            self.warranties.filter(
                is_deleted=False,
                warranty_start__lte=today,
                warranty_end__gte=today,
            )
            .order_by("warranty_end")
            .first()
        )

    def refresh_maintenance_snapshot(self, *, save: bool = True):
        latest_record = (
            self.service_records.filter(is_deleted=False).order_by("-service_date").first()
        )
        if latest_record:
            self.last_maintenance_date = latest_record.service_date
            if latest_record.next_maintenance_date:
                self.next_maintenance_date = latest_record.next_maintenance_date

        if save:
            self.save(
                update_fields=[
                    "last_maintenance_date",
                    "next_maintenance_date",
                    "updated_at",
                ]
            )


class MachineTagTypeChoices(models.TextChoices):
    NFC = "nfc", _("NFC")
    QR = "qr", _("QR")
    HYBRID = "hybrid", _("NFC + QR")


class MachineTag(OrganizationScopedModel):
    machine = models.ForeignKey(
        "machines.Machine",
        on_delete=models.PROTECT,
        related_name="tags",
        verbose_name=_("Машина"),
    )
    tag_type = models.CharField(
        _("Тип тега"),
        max_length=16,
        choices=MachineTagTypeChoices.choices,
        default=MachineTagTypeChoices.HYBRID,
    )
    public_token = models.CharField(
        _("Публичный токен"),
        max_length=48,
        unique=True,
        default=generate_public_token,
        db_index=True,
        help_text=_("Используется в публичном URL и не должен совпадать с внутренними ID."),
    )
    is_active = models.BooleanField(_("Активен"), default=True, db_index=True)
    issued_at = models.DateField(_("Дата выдачи"), default=timezone.localdate)
    replaced_at = models.DateTimeField(_("Дата замены"), null=True, blank=True)
    replacement_reason = models.CharField(_("Причина замены"), max_length=255, blank=True)
    previous_tag = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replacements",
        verbose_name=_("Предыдущий тег"),
    )

    class Meta:
        verbose_name = "Тег машины"
        verbose_name_plural = "Теги машин"
        ordering = ("-issued_at", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=["machine"],
                condition=models.Q(is_active=True, is_deleted=False),
                name="uniq_active_tag_per_machine",
            )
        ]

    def __str__(self) -> str:
        return f"{self.machine} / {self.get_tag_type_display()}"

    def clean(self):
        super().clean()
        if self.machine_id and not self.organization_id:
            self.organization_id = self.machine.organization_id
        if self.machine_id and self.machine.organization_id != self.organization_id:
            raise ValidationError(_("Тег должен принадлежать той же организации, что и машина."))

    def save(self, *args, **kwargs):
        if self.machine_id:
            self.organization_id = self.machine.organization_id
        if not self.is_active and self.replaced_at is None:
            self.replaced_at = timezone.now()
        super().save(*args, **kwargs)
