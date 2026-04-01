from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html
from unfold.contrib.filters.admin import (
    BooleanRadioFilter,
    ChoicesDropdownFilter,
    RelatedDropdownFilter,
)
from unfold.decorators import display

from apps.attachments.admin import AttachmentInline
from apps.core.admin import ScopeAwareAdmin, ScopeAwareTabularInline, admin_link
from apps.machines.models import (
    Machine,
    MachineStatusChoices,
    MachineTag,
    MachineTagTypeChoices,
)
from apps.service.models import ServiceRecord
from apps.warranties.models import Warranty


class MachineTagInline(ScopeAwareTabularInline):
    model = MachineTag
    fields = (
        "tag_type",
        "public_token",
        "is_active",
        "issued_at",
        "replaced_at",
        "replacement_reason",
    )
    readonly_fields = ("replaced_at",)


class WarrantyInline(ScopeAwareTabularInline):
    model = Warranty
    fields = ("warranty_type", "status", "warranty_start", "warranty_end", "public_summary")
    autocomplete_fields = ("organization",)


class ServiceRecordInline(ScopeAwareTabularInline):
    model = ServiceRecord
    extra = 0
    can_delete = False
    fields = (
        "service_date",
        "work_type",
        "engineer",
        "branch",
        "is_public",
        "next_maintenance_date",
    )
    readonly_fields = fields


@admin.register(Machine)
class MachineAdmin(ScopeAwareAdmin):
    actions = (
        "activate_selected",
        "deactivate_selected",
        "publish_selected",
        "hide_selected",
        "archive_selected",
        "restore_selected",
    )
    inlines = (MachineTagInline, WarrantyInline, ServiceRecordInline, AttachmentInline)
    list_display = (
        "name",
        "model_name",
        "serial_number",
        "status_badge",
        "dealer",
        "region",
        "branch",
        "warranty_badge",
        "next_maintenance_date",
        "public_badge",
        "public_link_short",
    )
    list_filter = (
        ("organization", RelatedDropdownFilter),
        ("dealer", RelatedDropdownFilter),
        ("region", RelatedDropdownFilter),
        ("branch", RelatedDropdownFilter),
        ("category", ChoicesDropdownFilter),
        ("status", ChoicesDropdownFilter),
        ("is_active", BooleanRadioFilter),
        ("is_public", BooleanRadioFilter),
    )
    search_fields = (
        "name",
        "model_name",
        "serial_number",
        "inventory_number",
        "dealer__name",
        "branch__name",
        "region__name",
    )
    ordering = ("organization__name", "name")
    autocomplete_fields = ("organization", "dealer", "branch", "region")
    list_select_related = ("organization", "dealer", "branch", "region")
    readonly_fields = (
        "public_page_link",
        "active_tag_display",
        "warranty_snapshot",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    fieldsets = (
        (
            "Идентификация",
            {
                "fields": (
                    ("organization", "is_active", "is_public"),
                    ("name", "model_name"),
                    ("serial_number", "inventory_number"),
                    ("category", "status"),
                )
            },
        ),
        (
            "Структура обслуживания",
            {
                "fields": (
                    ("dealer", "region", "branch"),
                    ("commissioning_date", "operating_hours"),
                    "emergency_phone",
                )
            },
        ),
        ("Описание", {"fields": ("photo", "description")}),
        (
            "Сервисные данные",
            {
                "fields": (
                    ("last_maintenance_date", "next_maintenance_date"),
                    "active_tag_display",
                    "warranty_snapshot",
                    "public_page_link",
                )
            },
        ),
        ("Система", {"classes": ("tab",), "fields": (("created_at", "updated_at"), "deleted_at")}),
    )

    @display(
        description="Статус машины",
        label={
            MachineStatusChoices.ACTIVE: "success",
            MachineStatusChoices.SERVICE: "warning",
            MachineStatusChoices.INACTIVE: "default",
            MachineStatusChoices.DECOMMISSIONED: "danger",
        },
    )
    def status_badge(self, obj: Machine):
        return (obj.status, obj.get_status_display())

    @display(description="Публикация", label={True: "success", False: "default"})
    def public_badge(self, obj: Machine):
        return (obj.is_public, "Доступен" if obj.is_public else "Скрыт")

    @display(
        description="Гарантия",
        label={
            "active": "success",
            "expiring": "warning",
            "expired": "danger",
            "none": "default",
        },
    )
    def warranty_badge(self, obj: Machine):
        warranty = obj.current_warranty
        if not warranty:
            return ("none", "Нет покрытия")
        return (warranty.status, warranty.get_status_display())

    @admin.display(description="Активный тег")
    def active_tag_display(self, obj: Machine) -> str:
        tag = obj.active_tag
        if not tag:
            return "—"
        return admin_link(tag, text=f"{tag.get_tag_type_display()} · {tag.public_token}")

    @admin.display(description="Публичный URL")
    def public_page_link(self, obj: Machine) -> str:
        tag = obj.active_tag
        if not tag:
            return "Активный тег не назначен"
        if not obj.is_public or not obj.is_active or obj.is_deleted:
            return "Машина снята с публикации"
        return format_html(
            (
                '<a href="/m/{}/" target="_blank" '
                'class="text-primary-700 dark:text-primary-400">/m/{}/</a>'
            ),
            tag.public_token,
            tag.public_token,
        )

    @admin.display(description="Паспорт")
    def public_link_short(self, obj: Machine) -> str:
        tag = obj.active_tag
        if not tag or not obj.is_public:
            return "—"
        return format_html(
            (
                '<a href="/m/{}/" target="_blank" '
                'class="text-primary-700 dark:text-primary-400">Открыть</a>'
            ),
            tag.public_token,
        )

    @admin.display(description="Снимок гарантии")
    def warranty_snapshot(self, obj: Machine) -> str:
        warranty = obj.current_warranty
        if not warranty:
            return "Покрытие не активно"
        return f"{warranty.get_warranty_type_display()} до {warranty.warranty_end:%d.%m.%Y}"

    def view_on_site(self, obj: Machine):
        tag = obj.active_tag
        if not tag:
            return None
        return f"/m/{tag.public_token}/"


@admin.register(MachineTag)
class MachineTagAdmin(ScopeAwareAdmin):
    actions = ("activate_selected", "deactivate_selected", "archive_selected", "restore_selected")
    list_display = (
        "machine_link",
        "tag_type_badge",
        "token_short",
        "is_active_badge",
        "issued_at",
        "replaced_at",
        "public_link",
    )
    list_filter = (
        ("organization", RelatedDropdownFilter),
        ("tag_type", ChoicesDropdownFilter),
        ("is_active", BooleanRadioFilter),
    )
    search_fields = ("public_token", "machine__name", "machine__serial_number")
    ordering = ("-issued_at",)
    autocomplete_fields = ("organization", "machine", "previous_tag")
    list_select_related = ("organization", "machine", "previous_tag")
    readonly_fields = ("public_link", "created_at", "updated_at", "deleted_at")
    fieldsets = (
        (
            "Тег",
            {"fields": (("organization", "machine"), ("tag_type", "is_active"), "public_token")},
        ),
        (
            "История",
            {
                "fields": (
                    ("issued_at", "replaced_at"),
                    "replacement_reason",
                    "previous_tag",
                    "public_link",
                )
            },
        ),
        ("Система", {"classes": ("tab",), "fields": (("created_at", "updated_at"), "deleted_at")}),
    )

    @admin.display(description="Машина")
    def machine_link(self, obj: MachineTag) -> str:
        return admin_link(obj.machine)

    @display(
        description="Тип",
        label={
            MachineTagTypeChoices.NFC: "info",
            MachineTagTypeChoices.QR: "primary",
            MachineTagTypeChoices.HYBRID: "success",
        },
    )
    def tag_type_badge(self, obj: MachineTag):
        return (obj.tag_type, obj.get_tag_type_display())

    @display(description="Статус", label={True: "success", False: "default"})
    def is_active_badge(self, obj: MachineTag):
        return (obj.is_active, "Активен" if obj.is_active else "Заменен")

    @admin.display(description="Токен")
    def token_short(self, obj: MachineTag) -> str:
        return f"{obj.public_token[:8]}..."

    @admin.display(description="Публичная ссылка")
    def public_link(self, obj: MachineTag) -> str:
        if not obj.machine.is_public or not obj.machine.is_active or obj.machine.is_deleted:
            return "Недоступно"
        return format_html(
            (
                '<a href="/m/{}/" target="_blank" '
                'class="text-primary-700 dark:text-primary-400">Открыть страницу</a>'
            ),
            obj.public_token,
        )

    def view_on_site(self, obj: MachineTag):
        if not obj.machine.is_public or not obj.machine.is_active or obj.machine.is_deleted:
            return None
        return f"/m/{obj.public_token}/"
