from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from apps.core.models import OrganizationScopedModel


class ServiceRequestSourceChoices(models.TextChoices):
    PUBLIC_PAGE = "public_page", _("Публичная страница")
    MANUAL = "manual", _("Ручное создание")
    PHONE = "phone", _("Телефон")
    INTERNAL = "internal", _("Внутренний канал")


class ServiceRequestStatusChoices(models.TextChoices):
    NEW = "new", _("Новая")
    TRIAGED = "triaged", _("Квалифицирована")
    SCHEDULED = "scheduled", _("Запланирована")
    IN_PROGRESS = "in_progress", _("В работе")
    WAITING_PARTS = "waiting_parts", _("Ожидание запчастей")
    COMPLETED = "completed", _("Выполнена")
    CLOSED = "closed", _("Закрыта")
    CANCELLED = "cancelled", _("Отменена")


class ServiceRequestPriorityChoices(models.TextChoices):
    LOW = "low", _("Низкий")
    NORMAL = "normal", _("Обычный")
    HIGH = "high", _("Высокий")
    CRITICAL = "critical", _("Критический")


class ServiceWorkTypeChoices(models.TextChoices):
    PREVENTIVE = "preventive", _("Плановое ТО")
    REPAIR = "repair", _("Ремонт")
    DIAGNOSTIC = "diagnostic", _("Диагностика")
    WARRANTY = "warranty", _("Гарантийные работы")
    INSPECTION = "inspection", _("Инспекция")
    COMMISSIONING = "commissioning", _("Ввод в эксплуатацию")
    OTHER = "other", _("Другое")


class ServiceRequest(OrganizationScopedModel):
    machine = models.ForeignKey(
        "machines.Machine",
        on_delete=models.PROTECT,
        related_name="service_requests",
        verbose_name=_("Машина"),
    )
    dealer = models.ForeignKey(
        "dealers.Dealer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_requests",
        verbose_name=_("Дилер"),
    )
    source = models.CharField(
        _("Источник"),
        max_length=16,
        choices=ServiceRequestSourceChoices.choices,
        default=ServiceRequestSourceChoices.MANUAL,
        db_index=True,
    )
    client_name = models.CharField(_("Имя клиента"), max_length=255)
    client_phone = PhoneNumberField(_("Телефон клиента"))
    client_company = models.CharField(_("Компания клиента"), max_length=255, blank=True)
    problem_description = models.TextField(_("Описание проблемы"))
    status = models.CharField(
        _("Статус"),
        max_length=24,
        choices=ServiceRequestStatusChoices.choices,
        default=ServiceRequestStatusChoices.NEW,
        db_index=True,
    )
    priority = models.CharField(
        _("Приоритет"),
        max_length=16,
        choices=ServiceRequestPriorityChoices.choices,
        default=ServiceRequestPriorityChoices.NORMAL,
        db_index=True,
    )
    region = models.ForeignKey(
        "branches.Region",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_requests",
        verbose_name=_("Регион"),
    )
    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_requests",
        verbose_name=_("Филиал"),
    )
    assigned_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_service_requests",
        verbose_name=_("Ответственный менеджер"),
    )
    assigned_engineer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_service_requests",
        verbose_name=_("Ответственный инженер"),
    )
    due_at = models.DateTimeField(_("Срок реакции"), null=True, blank=True)
    first_response_at = models.DateTimeField(_("Первый ответ"), null=True, blank=True)
    resolved_at = models.DateTimeField(_("Решено"), null=True, blank=True)
    closed_at = models.DateTimeField(_("Закрыто"), null=True, blank=True)
    consent_to_processing = models.BooleanField(_("Согласие на обработку данных"), default=False)
    routing_applied = models.BooleanField(_("Маршрутизация применена"), default=False)
    internal_note = models.TextField(_("Внутренняя заметка"), blank=True)
    attachments = GenericRelation(
        "attachments.Attachment",
        related_query_name="service_request",
        verbose_name=_("Вложения"),
    )

    class Meta:
        verbose_name = "Сервисная заявка"
        verbose_name_plural = "Сервисные заявки"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["organization", "status", "priority"]),
            models.Index(fields=["organization", "region", "branch"]),
            models.Index(fields=["organization", "due_at"]),
        ]

    def __str__(self) -> str:
        return f"#{self.pk or 'new'} / {self.machine}"

    def clean(self):
        super().clean()
        if self.machine_id and not self.organization_id:
            self.organization_id = self.machine.organization_id
        if self.machine_id and self.machine.organization_id != self.organization_id:
            raise ValidationError(_("Заявка должна принадлежать той же организации, что и машина."))

        if (
            self.branch_id
            and self.organization_id
            and self.branch.organization_id != self.organization_id
        ):
            raise ValidationError(_("Филиал заявки должен принадлежать выбранной организации."))

        if (
            self.region_id
            and self.organization_id
            and self.region.organization_id != self.organization_id
        ):
            raise ValidationError(_("Регион заявки должен принадлежать выбранной организации."))

        if self.branch_id and self.region_id and self.branch.region_id != self.region_id:
            raise ValidationError(_("Филиал заявки должен соответствовать выбранному региону."))

        if (
            self.dealer_id
            and self.organization_id
            and self.dealer.organization_id != self.organization_id
        ):
            raise ValidationError(_("Дилер заявки должен принадлежать выбранной организации."))

    def apply_machine_routing(self):
        if not self.machine_id:
            return

        self.organization_id = self.machine.organization_id
        self.region_id = self.region_id or self.machine.region_id
        self.branch_id = self.branch_id or self.machine.branch_id
        self.dealer_id = self.dealer_id or self.machine.dealer_id
        self.routing_applied = bool(self.region_id or self.branch_id or self.dealer_id)

    @property
    def is_overdue(self) -> bool:
        return bool(
            self.due_at
            and self.status
            not in {ServiceRequestStatusChoices.COMPLETED, ServiceRequestStatusChoices.CLOSED}
            and self.due_at < timezone.now()
        )

    def save(self, *args, **kwargs):
        self.apply_machine_routing()
        if self.source == ServiceRequestSourceChoices.PUBLIC_PAGE:
            self.status = ServiceRequestStatusChoices.NEW
        if self.status == ServiceRequestStatusChoices.CLOSED and self.closed_at is None:
            self.closed_at = timezone.now()
        if self.status == ServiceRequestStatusChoices.COMPLETED and self.resolved_at is None:
            self.resolved_at = timezone.now()
        super().save(*args, **kwargs)


class ServiceRecord(OrganizationScopedModel):
    machine = models.ForeignKey(
        "machines.Machine",
        on_delete=models.PROTECT,
        related_name="service_records",
        verbose_name=_("Машина"),
    )
    service_request = models.ForeignKey(
        "service.ServiceRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_records",
        verbose_name=_("Связанная заявка"),
    )
    service_date = models.DateField(_("Дата обслуживания"))
    work_type = models.CharField(
        _("Тип работ"),
        max_length=24,
        choices=ServiceWorkTypeChoices.choices,
        default=ServiceWorkTypeChoices.PREVENTIVE,
    )
    description = models.TextField(_("Описание работ"))
    engineer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_records",
        verbose_name=_("Инженер"),
    )
    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_records",
        verbose_name=_("Филиал"),
    )
    operating_hours = models.PositiveIntegerField(_("Наработка, моточасы"), null=True, blank=True)
    mileage_km = models.PositiveIntegerField(_("Пробег, км"), null=True, blank=True)
    public_summary = models.TextField(_("Публичное резюме"), blank=True)
    is_public = models.BooleanField(_("Показывать публично"), default=False, db_index=True)
    private_notes = models.TextField(_("Внутренние заметки"), blank=True)
    next_maintenance_date = models.DateField(
        _("Следующая дата обслуживания"),
        null=True,
        blank=True,
    )
    attachments = GenericRelation(
        "attachments.Attachment",
        related_query_name="service_record",
        verbose_name=_("Вложения"),
    )

    class Meta:
        verbose_name = "Сервисная запись"
        verbose_name_plural = "Сервисные записи"
        ordering = ("-service_date", "-created_at")
        indexes = [
            models.Index(fields=["organization", "service_date"]),
            models.Index(fields=["organization", "is_public"]),
        ]

    def __str__(self) -> str:
        return f"{self.machine} / {self.service_date:%d.%m.%Y}"

    def clean(self):
        super().clean()
        if self.machine_id and not self.organization_id:
            self.organization_id = self.machine.organization_id
        if self.machine_id and self.machine.organization_id != self.organization_id:
            raise ValidationError(
                _("Сервисная запись должна принадлежать той же организации, что и машина.")
            )
        if (
            self.branch_id
            and self.organization_id
            and self.branch.organization_id != self.organization_id
        ):
            raise ValidationError(
                _("Филиал сервисной записи должен принадлежать организации машины.")
            )
        if self.service_request_id and self.service_request.machine_id != self.machine_id:
            raise ValidationError(_("Связанная заявка должна относиться к той же машине."))

    def save(self, *args, **kwargs):
        if self.machine_id:
            self.organization_id = self.machine.organization_id
            self.branch_id = self.branch_id or self.machine.branch_id
        super().save(*args, **kwargs)
        self.machine.refresh_maintenance_snapshot()
