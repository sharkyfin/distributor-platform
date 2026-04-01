from __future__ import annotations

from django.contrib import admin
from django.db.models import Count, Q
from unfold.decorators import display

from apps.core.admin import ScopeAwareAdmin
from apps.organizations.models import Organization


@admin.register(Organization)
class OrganizationAdmin(ScopeAwareAdmin):
    actions = ("activate_selected", "deactivate_selected", "archive_selected", "restore_selected")
    list_display = (
        "name",
        "code",
        "is_active_badge",
        "regions_total",
        "branches_total",
        "dealers_total",
        "machines_total",
        "updated_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "code", "legal_name", "inn", "email")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at", "deleted_at")
    fieldsets = (
        (
            "Профиль",
            {
                "fields": (
                    ("name", "code"),
                    ("legal_name", "inn"),
                    ("phone", "email"),
                    "website",
                    "address",
                    "is_active",
                )
            },
        ),
        ("Система", {"classes": ("tab",), "fields": (("created_at", "updated_at"), "deleted_at")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _regions_total=Count(
                "branches_region_set",
                filter=Q(branches_region_set__is_deleted=False),
                distinct=True,
            ),
            _branches_total=Count(
                "branches_branch_set",
                filter=Q(branches_branch_set__is_deleted=False),
                distinct=True,
            ),
            _dealers_total=Count(
                "dealers_dealer_set",
                filter=Q(dealers_dealer_set__is_deleted=False),
                distinct=True,
            ),
            _machines_total=Count(
                "machines_machine_set",
                filter=Q(machines_machine_set__is_deleted=False),
                distinct=True,
            ),
        )

    @display(description="Статус", label={True: "success", False: "danger"})
    def is_active_badge(self, obj: Organization):
        return (obj.is_active, "Активна" if obj.is_active else "Отключена")

    @admin.display(description="Регионы", ordering="_regions_total")
    def regions_total(self, obj: Organization) -> int:
        return obj._regions_total

    @admin.display(description="Филиалы", ordering="_branches_total")
    def branches_total(self, obj: Organization) -> int:
        return obj._branches_total

    @admin.display(description="Дилеры", ordering="_dealers_total")
    def dealers_total(self, obj: Organization) -> int:
        return obj._dealers_total

    @admin.display(description="Машины", ordering="_machines_total")
    def machines_total(self, obj: Organization) -> int:
        return obj._machines_total
