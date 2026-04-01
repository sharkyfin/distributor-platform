from __future__ import annotations

from django.contrib import admin
from django.utils import timezone
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RelatedDropdownFilter
from unfold.decorators import display

from apps.core.admin import ScopeAwareAdmin, admin_link
from apps.warranties.models import Warranty, WarrantyStatusChoices, WarrantyTypeChoices


@admin.register(Warranty)
class WarrantyAdmin(ScopeAwareAdmin):
    actions = ("archive_selected", "restore_selected")
    list_display = (
        "machine_link",
        "warranty_type_badge",
        "status_badge",
        "warranty_start",
        "warranty_end",
        "days_remaining",
        "organization",
    )
    list_filter = (
        ("organization", RelatedDropdownFilter),
        ("machine__dealer", RelatedDropdownFilter),
        ("status", ChoicesDropdownFilter),
        ("warranty_type", ChoicesDropdownFilter),
    )
    search_fields = ("machine__name", "machine__serial_number", "public_summary", "notes")
    ordering = ("warranty_end",)
    autocomplete_fields = ("organization", "machine")
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    fieldsets = (
        (
            "Гарантийный блок",
            {
                "fields": (
                    ("organization", "machine"),
                    ("warranty_type", "status"),
                    ("warranty_start", "warranty_end"),
                    "public_summary",
                )
            },
        ),
        ("Внутренние заметки", {"fields": ("notes",)}),
        ("Система", {"classes": ("tab",), "fields": (("created_at", "updated_at"), "deleted_at")}),
    )

    @admin.display(description="Машина")
    def machine_link(self, obj: Warranty) -> str:
        return admin_link(obj.machine)

    @display(
        description="Тип гарантии",
        label={
            WarrantyTypeChoices.STANDARD: "primary",
            WarrantyTypeChoices.EXTENDED: "success",
            WarrantyTypeChoices.POWERTRAIN: "warning",
            WarrantyTypeChoices.SERVICE_CONTRACT: "info",
            WarrantyTypeChoices.OTHER: "default",
        },
    )
    def warranty_type_badge(self, obj: Warranty):
        return (obj.warranty_type, obj.get_warranty_type_display())

    @display(
        description="Статус",
        label={
            WarrantyStatusChoices.ACTIVE: "success",
            WarrantyStatusChoices.EXPIRING: "warning",
            WarrantyStatusChoices.EXPIRED: "danger",
            WarrantyStatusChoices.VOID: "danger",
            WarrantyStatusChoices.PENDING: "info",
        },
    )
    def status_badge(self, obj: Warranty):
        return (obj.status, obj.get_status_display())

    @admin.display(description="Осталось дней")
    def days_remaining(self, obj: Warranty) -> int | str:
        return max((obj.warranty_end - timezone.localdate()).days, 0) if obj.warranty_end else "—"
