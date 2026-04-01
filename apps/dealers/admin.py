from __future__ import annotations

from django.contrib import admin
from django.db.models import Count, Q
from unfold.contrib.filters.admin import (
    BooleanRadioFilter,
    ChoicesDropdownFilter,
    RelatedDropdownFilter,
)
from unfold.decorators import display

from apps.core.admin import ScopeAwareAdmin, ScopeAwareTabularInline
from apps.dealers.models import (
    Contact,
    ContactTypeChoices,
    ContactVisibilityChoices,
    Dealer,
)


class ContactInline(ScopeAwareTabularInline):
    model = Contact
    extra = 0
    fields = ("full_name", "title", "contact_type", "phone", "email", "visibility", "is_primary")
    autocomplete_fields = ("organization", "branch")


@admin.register(Dealer)
class DealerAdmin(ScopeAwareAdmin):
    actions = ("activate_selected", "deactivate_selected", "archive_selected", "restore_selected")
    inlines = (ContactInline,)
    list_display = (
        "name",
        "code",
        "organization",
        "branches_total",
        "contacts_total",
        "machines_total",
        "is_active_badge",
    )
    list_filter = (("organization", RelatedDropdownFilter), ("is_active", BooleanRadioFilter))
    search_fields = ("name", "code", "legal_name", "phone", "email", "organization__name")
    ordering = ("organization__name", "name")
    autocomplete_fields = ("organization",)
    filter_horizontal = ("branches",)
    fieldsets = (
        ("Профиль", {"fields": (("organization", "is_active"), ("name", "code"), "legal_name")}),
        ("Контакты", {"fields": (("phone", "emergency_phone"), ("email", "website"), "address")}),
        ("Филиалы покрытия", {"fields": ("branches",)}),
        ("Система", {"classes": ("tab",), "fields": (("created_at", "updated_at"), "deleted_at")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _branches_total=Count("branches", filter=Q(branches__is_deleted=False), distinct=True),
            _contacts_total=Count("contacts", filter=Q(contacts__is_deleted=False), distinct=True),
            _machines_total=Count("machines", filter=Q(machines__is_deleted=False), distinct=True),
        )

    @display(description="Статус", label={True: "success", False: "danger"})
    def is_active_badge(self, obj: Dealer):
        return (obj.is_active, "Активен" if obj.is_active else "Архив")

    @admin.display(description="Филиалы", ordering="_branches_total")
    def branches_total(self, obj: Dealer) -> int:
        return obj._branches_total

    @admin.display(description="Контакты", ordering="_contacts_total")
    def contacts_total(self, obj: Dealer) -> int:
        return obj._contacts_total

    @admin.display(description="Машины", ordering="_machines_total")
    def machines_total(self, obj: Dealer) -> int:
        return obj._machines_total


@admin.register(Contact)
class ContactAdmin(ScopeAwareAdmin):
    actions = ("archive_selected", "restore_selected", "publish_selected", "hide_selected")
    list_display = (
        "full_name",
        "title",
        "contact_type_badge",
        "visibility_badge",
        "organization",
        "dealer",
        "branch",
        "is_primary",
    )
    list_filter = (
        ("organization", RelatedDropdownFilter),
        ("dealer", RelatedDropdownFilter),
        ("branch", RelatedDropdownFilter),
        ("contact_type", ChoicesDropdownFilter),
        ("visibility", ChoicesDropdownFilter),
    )
    search_fields = (
        "full_name",
        "title",
        "phone",
        "email",
        "dealer__name",
        "branch__name",
        "organization__name",
    )
    ordering = ("organization__name", "full_name")
    autocomplete_fields = ("organization", "dealer", "branch")
    fieldsets = (
        (
            "Контакт",
            {
                "fields": (
                    ("organization", "is_primary"),
                    ("dealer", "branch"),
                    ("full_name", "title"),
                )
            },
        ),
        (
            "Канал связи",
            {
                "fields": (
                    ("phone", "email"),
                    ("contact_type", "visibility"),
                    "public_note",
                    "private_note",
                )
            },
        ),
        ("Система", {"classes": ("tab",), "fields": (("created_at", "updated_at"), "deleted_at")}),
    )

    @display(
        description="Тип",
        label={
            ContactTypeChoices.SERVICE: "primary",
            ContactTypeChoices.EMERGENCY: "danger",
            ContactTypeChoices.MANAGER: "info",
            ContactTypeChoices.SALES: "warning",
            ContactTypeChoices.OPERATOR: "success",
            ContactTypeChoices.OTHER: "default",
        },
    )
    def contact_type_badge(self, obj: Contact):
        return (obj.contact_type, obj.get_contact_type_display())

    @display(
        description="Видимость",
        label={
            ContactVisibilityChoices.PUBLIC: "success",
            ContactVisibilityChoices.INTERNAL: "default",
        },
    )
    def visibility_badge(self, obj: Contact):
        return (obj.visibility, obj.get_visibility_display())
