from __future__ import annotations

from django.contrib import admin
from django.db.models import Count, Q
from unfold.contrib.filters.admin import BooleanRadioFilter, RelatedDropdownFilter
from unfold.decorators import display

from apps.branches.models import Branch, Region
from apps.core.admin import ScopeAwareAdmin, ScopeAwareTabularInline
from apps.dealers.models import Contact


class BranchContactInline(ScopeAwareTabularInline):
    model = Contact
    fk_name = "branch"
    extra = 0
    fields = ("full_name", "title", "contact_type", "phone", "email", "visibility", "is_primary")
    autocomplete_fields = ("organization", "dealer")


@admin.register(Region)
class RegionAdmin(ScopeAwareAdmin):
    actions = ("activate_selected", "deactivate_selected", "archive_selected", "restore_selected")
    list_display = ("name", "code", "organization", "ordering", "is_active_badge", "branches_total")
    list_filter = ("organization", ("is_active", BooleanRadioFilter))
    search_fields = ("name", "code", "organization__name")
    ordering = ("organization__name", "ordering", "name")
    autocomplete_fields = ("organization",)
    list_editable = ("ordering",)
    fieldsets = (
        (
            "Позиционирование",
            {"fields": (("organization", "is_active"), ("name", "code"), "ordering")},
        ),
        ("Система", {"classes": ("tab",), "fields": (("created_at", "updated_at"), "deleted_at")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _branches_total=Count("branches", filter=Q(branches__is_deleted=False), distinct=True)
        )

    @display(description="Статус", label={True: "success", False: "danger"})
    def is_active_badge(self, obj: Region):
        return (obj.is_active, "Активен" if obj.is_active else "Архив")

    @admin.display(description="Филиалы", ordering="_branches_total")
    def branches_total(self, obj: Region) -> int:
        return obj._branches_total


@admin.register(Branch)
class BranchAdmin(ScopeAwareAdmin):
    actions = ("activate_selected", "deactivate_selected", "archive_selected", "restore_selected")
    inlines = (BranchContactInline,)
    list_display = (
        "name",
        "region",
        "organization",
        "service_phone",
        "emergency_phone",
        "machines_total",
        "dealers_total",
        "is_active_badge",
    )
    list_filter = (
        ("organization", RelatedDropdownFilter),
        ("region", RelatedDropdownFilter),
        ("is_active", BooleanRadioFilter),
    )
    search_fields = (
        "name",
        "code",
        "address",
        "service_email",
        "organization__name",
        "region__name",
    )
    ordering = ("organization__name", "region__ordering", "name")
    autocomplete_fields = ("organization", "region")
    fieldsets = (
        ("Структура", {"fields": (("organization", "region"), ("name", "code"), "is_active")}),
        (
            "Контакты",
            {
                "fields": (
                    ("phone", "service_phone"),
                    ("emergency_phone", "service_email"),
                    "address",
                    "service_contact_info",
                )
            },
        ),
        ("Система", {"classes": ("tab",), "fields": (("created_at", "updated_at"), "deleted_at")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _machines_total=Count("machines", filter=Q(machines__is_deleted=False), distinct=True),
            _dealers_total=Count("dealers", filter=Q(dealers__is_deleted=False), distinct=True),
        )

    @display(description="Статус", label={True: "success", False: "danger"})
    def is_active_badge(self, obj: Branch):
        return (obj.is_active, "Работает" if obj.is_active else "Архив")

    @admin.display(description="Машины", ordering="_machines_total")
    def machines_total(self, obj: Branch) -> int:
        return obj._machines_total

    @admin.display(description="Дилеры", ordering="_dealers_total")
    def dealers_total(self, obj: Branch) -> int:
        return obj._dealers_total
