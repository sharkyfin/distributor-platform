from __future__ import annotations

from datetime import timedelta

from django.contrib import admin
from django.utils import timezone
from unfold.contrib.filters.admin import (
    BooleanRadioFilter,
    ChoicesDropdownFilter,
    RangeDateFilter,
    RangeDateTimeFilter,
    RelatedDropdownFilter,
)
from unfold.decorators import display

from apps.attachments.admin import AttachmentInline
from apps.core.admin import ScopeAwareAdmin, admin_link
from apps.service.models import (
    ServiceRecord,
    ServiceRequest,
    ServiceRequestPriorityChoices,
    ServiceRequestSourceChoices,
    ServiceRequestStatusChoices,
    ServiceWorkTypeChoices,
)


class OverdueRequestFilter(admin.SimpleListFilter):
    title = "Срок реакции"
    parameter_name = "sla"

    def lookups(self, request, model_admin):
        return (("overdue", "Просрочено"), ("due_soon", "Срок сегодня/завтра"))

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == "overdue":
            return queryset.filter(due_at__lt=now).exclude(
                status__in=[
                    ServiceRequestStatusChoices.COMPLETED,
                    ServiceRequestStatusChoices.CLOSED,
                    ServiceRequestStatusChoices.CANCELLED,
                ]
            )
        if self.value() == "due_soon":
            return queryset.filter(due_at__lte=now + timedelta(days=1)).exclude(
                status__in=[
                    ServiceRequestStatusChoices.COMPLETED,
                    ServiceRequestStatusChoices.CLOSED,
                    ServiceRequestStatusChoices.CANCELLED,
                ]
            )
        return queryset


@admin.register(ServiceRequest)
class ServiceRequestAdmin(ScopeAwareAdmin):
    actions = ("archive_selected", "restore_selected")
    inlines = (AttachmentInline,)
    list_display = (
        "request_number",
        "machine_link",
        "status_badge",
        "priority_badge",
        "source_badge",
        "region",
        "branch",
        "assigned_manager",
        "assigned_engineer",
        "sla_badge",
        "created_at",
    )
    list_filter = (
        ("organization", RelatedDropdownFilter),
        ("dealer", RelatedDropdownFilter),
        ("region", RelatedDropdownFilter),
        ("branch", RelatedDropdownFilter),
        ("status", ChoicesDropdownFilter),
        ("priority", ChoicesDropdownFilter),
        ("source", ChoicesDropdownFilter),
        ("created_at", RangeDateTimeFilter),
        OverdueRequestFilter,
    )
    search_fields = (
        "machine__name",
        "machine__serial_number",
        "client_name",
        "client_phone",
        "client_company",
        "problem_description",
    )
    ordering = ("-created_at",)
    autocomplete_fields = (
        "organization",
        "machine",
        "dealer",
        "region",
        "branch",
        "assigned_manager",
        "assigned_engineer",
    )
    list_select_related = (
        "organization",
        "machine",
        "dealer",
        "region",
        "branch",
        "assigned_manager",
        "assigned_engineer",
    )
    readonly_fields = (
        "routing_summary",
        "created_at",
        "updated_at",
        "deleted_at",
        "resolved_at",
        "closed_at",
    )
    fieldsets = (
        (
            "Обращение",
            {
                "fields": (
                    ("organization", "machine"),
                    ("source", "status", "priority"),
                    "problem_description",
                )
            },
        ),
        (
            "Клиент",
            {
                "fields": (
                    ("client_name", "client_phone"),
                    "client_company",
                    "consent_to_processing",
                )
            },
        ),
        ("Маршрутизация", {"fields": (("dealer", "region", "branch"), "routing_summary")}),
        (
            "Исполнение",
            {
                "fields": (
                    ("assigned_manager", "assigned_engineer"),
                    "due_at",
                    "internal_note",
                )
            },
        ),
        ("Закрытие", {"fields": (("resolved_at", "closed_at"),)}),
        ("Система", {"classes": ("tab",), "fields": (("created_at", "updated_at"), "deleted_at")}),
    )

    @admin.display(description="#")
    def request_number(self, obj: ServiceRequest) -> str:
        return f"SR-{obj.pk}"

    @admin.display(description="Машина")
    def machine_link(self, obj: ServiceRequest) -> str:
        return admin_link(obj.machine)

    @display(
        description="Статус",
        label={
            ServiceRequestStatusChoices.NEW: "primary",
            ServiceRequestStatusChoices.TRIAGED: "info",
            ServiceRequestStatusChoices.SCHEDULED: "warning",
            ServiceRequestStatusChoices.IN_PROGRESS: "warning",
            ServiceRequestStatusChoices.WAITING_PARTS: "warning",
            ServiceRequestStatusChoices.COMPLETED: "success",
            ServiceRequestStatusChoices.CLOSED: "default",
            ServiceRequestStatusChoices.CANCELLED: "danger",
        },
    )
    def status_badge(self, obj: ServiceRequest):
        return (obj.status, obj.get_status_display())

    @display(
        description="Приоритет",
        label={
            ServiceRequestPriorityChoices.LOW: "default",
            ServiceRequestPriorityChoices.NORMAL: "primary",
            ServiceRequestPriorityChoices.HIGH: "warning",
            ServiceRequestPriorityChoices.CRITICAL: "danger",
        },
    )
    def priority_badge(self, obj: ServiceRequest):
        return (obj.priority, obj.get_priority_display())

    @display(
        description="Источник",
        label={
            ServiceRequestSourceChoices.PUBLIC_PAGE: "success",
            ServiceRequestSourceChoices.MANUAL: "default",
            ServiceRequestSourceChoices.PHONE: "info",
            ServiceRequestSourceChoices.INTERNAL: "primary",
        },
    )
    def source_badge(self, obj: ServiceRequest):
        return (obj.source, obj.get_source_display())

    @display(
        description="Срок реакции",
        label={"ok": "success", "soon": "warning", "overdue": "danger"},
    )
    def sla_badge(self, obj: ServiceRequest):
        if not obj.due_at:
            return ("ok", "Не задан")
        if obj.is_overdue:
            return ("overdue", "Просрочено")
        if obj.due_at <= timezone.now() + timedelta(days=1):
            return ("soon", "Срок близко")
        return ("ok", "В срок")

    @admin.display(description="Маршрутизация")
    def routing_summary(self, obj: ServiceRequest) -> str:
        parts = [part for part in [obj.dealer, obj.region, obj.branch] if part]
        return (
            " / ".join(str(part) for part in parts)
            if parts
            else "Будет определена автоматически"
        )


@admin.register(ServiceRecord)
class ServiceRecordAdmin(ScopeAwareAdmin):
    actions = ("archive_selected", "restore_selected", "publish_selected", "hide_selected")
    inlines = (AttachmentInline,)
    list_display = (
        "machine_link",
        "service_date",
        "work_type_badge",
        "engineer",
        "branch",
        "public_badge",
        "next_maintenance_date",
    )
    list_filter = (
        ("organization", RelatedDropdownFilter),
        ("branch", RelatedDropdownFilter),
        ("work_type", ChoicesDropdownFilter),
        ("is_public", BooleanRadioFilter),
        ("service_date", RangeDateFilter),
    )
    search_fields = (
        "machine__name",
        "machine__serial_number",
        "description",
        "public_summary",
        "private_notes",
    )
    ordering = ("-service_date", "-created_at")
    autocomplete_fields = ("organization", "machine", "service_request", "engineer", "branch")
    list_select_related = ("organization", "machine", "service_request", "engineer", "branch")
    readonly_fields = ("service_request_link", "created_at", "updated_at", "deleted_at")
    fieldsets = (
        (
            "Работы",
            {
                "fields": (
                    ("organization", "machine"),
                    "service_request_link",
                    ("service_date", "work_type"),
                    "description",
                )
            },
        ),
        (
            "Исполнитель",
            {
                "fields": (
                    ("engineer", "branch"),
                    ("operating_hours", "mileage_km"),
                    "next_maintenance_date",
                )
            },
        ),
        ("Публикация", {"fields": (("is_public",), "public_summary")}),
        ("Внутренние заметки", {"fields": ("private_notes",)}),
        ("Система", {"classes": ("tab",), "fields": (("created_at", "updated_at"), "deleted_at")}),
    )

    @admin.display(description="Машина")
    def machine_link(self, obj: ServiceRecord) -> str:
        return admin_link(obj.machine)

    @admin.display(description="Заявка")
    def service_request_link(self, obj: ServiceRecord) -> str:
        return admin_link(obj.service_request) if obj.service_request else "—"

    @display(
        description="Тип работ",
        label={
            ServiceWorkTypeChoices.PREVENTIVE: "primary",
            ServiceWorkTypeChoices.REPAIR: "warning",
            ServiceWorkTypeChoices.DIAGNOSTIC: "info",
            ServiceWorkTypeChoices.WARRANTY: "success",
            ServiceWorkTypeChoices.INSPECTION: "default",
            ServiceWorkTypeChoices.COMMISSIONING: "primary",
            ServiceWorkTypeChoices.OTHER: "default",
        },
    )
    def work_type_badge(self, obj: ServiceRecord):
        return (obj.work_type, obj.get_work_type_display())

    @display(description="Публично", label={True: "success", False: "default"})
    def public_badge(self, obj: ServiceRecord):
        return (obj.is_public, "Да" if obj.is_public else "Нет")
