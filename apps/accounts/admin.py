from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count
from django.utils.translation import gettext_lazy as _
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RelatedDropdownFilter
from unfold.decorators import display

from apps.accounts.models import User, UserProfile, UserRoleChoices
from apps.core.admin import ScopeAwareAdmin, ScopeAwareStackedInline


class UserProfileInline(ScopeAwareStackedInline):
    model = UserProfile
    can_delete = False
    fields = (("role", "organization"), ("dealer", "region", "branch"), "notes")
    autocomplete_fields = ("organization", "dealer", "region", "branch")


class UserRoleFilter(admin.SimpleListFilter):
    title = "Роль"
    parameter_name = "role"

    def lookups(self, request, model_admin):
        return UserRoleChoices.choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(profile__role=self.value())
        return queryset


@admin.register(User)
class UserAdmin(DjangoUserAdmin, ScopeAwareAdmin):
    inlines = (UserProfileInline,)
    list_display = (
        "email",
        "full_name",
        "role_badge",
        "position",
        "phone",
        "is_staff",
        "is_active",
        "last_login",
    )
    list_filter = (UserRoleFilter, "is_staff", "is_active", "is_superuser")
    search_fields = ("email", "first_name", "last_name", "middle_name", "phone", "profile__notes")
    ordering = ("email",)
    list_select_related = ("profile",)
    readonly_fields = ("last_login", "date_joined")
    fieldsets = (
        (_("Учетная запись"), {"fields": (("email", "password"),)}),
        (
            _("Личные данные"),
            {"fields": (("last_name", "first_name", "middle_name"), ("position", "phone"))},
        ),
        (
            _("Доступ"),
            {"fields": (("is_active", "is_staff", "is_superuser"), "groups", "user_permissions")},
        ),
        (_("Служебные метки"), {"fields": (("last_login", "date_joined"),)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    ("first_name", "last_name"),
                    ("position", "phone"),
                    ("password1", "password2"),
                    ("is_active", "is_staff"),
                ),
            },
        ),
    )
    filter_horizontal = ("groups", "user_permissions")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("profile")

    @admin.display(description="ФИО")
    def full_name(self, obj: User) -> str:
        return obj.get_full_name() or "—"

    @display(
        description="Роль",
        label={
            UserRoleChoices.SUPER_ADMIN: "danger",
            UserRoleChoices.DISTRIBUTOR_ADMIN: "primary",
            UserRoleChoices.DEALER_ADMIN: "info",
            UserRoleChoices.SERVICE_MANAGER: "warning",
            UserRoleChoices.SERVICE_ENGINEER: "success",
            UserRoleChoices.INTERNAL_OPERATOR: "default",
            UserRoleChoices.UNASSIGNED: "default",
        },
    )
    def role_badge(self, obj: User):
        role = obj.profile.role if hasattr(obj, "profile") else UserRoleChoices.UNASSIGNED
        label = obj.profile.get_role_display() if hasattr(obj, "profile") else "Не назначено"
        return (role, label)


@admin.register(UserProfile)
class UserProfileAdmin(ScopeAwareAdmin):
    list_display = (
        "user",
        "role_badge",
        "organization",
        "dealer",
        "region",
        "branch",
        "access_summary",
    )
    list_filter = (
        ("organization", RelatedDropdownFilter),
        ("dealer", RelatedDropdownFilter),
        ("branch", RelatedDropdownFilter),
        ("role", ChoicesDropdownFilter),
    )
    search_fields = ("user__email", "user__first_name", "user__last_name", "notes")
    ordering = ("user__email",)
    autocomplete_fields = ("user", "organization", "dealer", "region", "branch")
    fieldsets = (
        (
            "Роль и доступ",
            {"fields": ("user", "role", ("organization", "dealer"), ("region", "branch"))},
        ),
        ("Комментарий", {"fields": ("notes",)}),
        ("Система", {"classes": ("tab",), "fields": (("created_at", "updated_at"),)}),
    )

    @display(
        description="Роль",
        label={
            UserRoleChoices.SUPER_ADMIN: "danger",
            UserRoleChoices.DISTRIBUTOR_ADMIN: "primary",
            UserRoleChoices.DEALER_ADMIN: "info",
            UserRoleChoices.SERVICE_MANAGER: "warning",
            UserRoleChoices.SERVICE_ENGINEER: "success",
            UserRoleChoices.INTERNAL_OPERATOR: "default",
            UserRoleChoices.UNASSIGNED: "default",
        },
    )
    def role_badge(self, obj: UserProfile):
        return (obj.role, obj.get_role_display())

    @admin.display(description="Контур доступа")
    def access_summary(self, obj: UserProfile) -> str:
        return obj.scope_summary


try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


@admin.register(Group)
class GroupAdmin(ScopeAwareAdmin):
    list_display = ("name", "users_total")
    search_fields = ("name",)
    filter_horizontal = ("permissions",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_users_total=Count("user"))

    @admin.display(description="Пользователи", ordering="_users_total")
    def users_total(self, obj: Group) -> int:
        return obj._users_total
