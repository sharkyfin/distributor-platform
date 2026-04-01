from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib import admin, messages
from django.db.models import Q, QuerySet
from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import GenericTabularInline, ModelAdmin, StackedInline, TabularInline

admin.site.site_header = "Сервисный паспорт спецтехники"
admin.site.site_title = "Цифровой сервисный паспорт"
admin.site.index_title = "Панель управления"


def get_user_profile(user):
    return getattr(user, "profile", None)


def get_effective_organization_id(user) -> int | None:
    profile = get_user_profile(user)
    if not profile:
        return None

    if profile.organization_id:
        return profile.organization_id
    if profile.dealer_id and profile.dealer:
        return profile.dealer.organization_id
    if profile.branch_id and profile.branch:
        return profile.branch.organization_id
    if profile.region_id and profile.region:
        return profile.region.organization_id
    return None


def _model_field_names(model) -> set[str]:
    return {field.name for field in model._meta.get_fields() if hasattr(field, "name")}


def _apply_dealer_scope(queryset: QuerySet, dealer_id: int) -> QuerySet:
    model = queryset.model
    model_name = model._meta.model_name
    fields = _model_field_names(model)

    if "dealer" in fields:
        return queryset.filter(dealer_id=dealer_id)
    if model_name == "dealer":
        return queryset.filter(pk=dealer_id)
    if "machine" in fields:
        return queryset.filter(machine__dealer_id=dealer_id)
    if "service_request" in fields:
        return queryset.filter(service_request__dealer_id=dealer_id)
    if model_name == "branch":
        return queryset.filter(dealers__id=dealer_id)
    if model_name == "contact":
        return queryset.filter(Q(dealer_id=dealer_id) | Q(branch__dealers__id=dealer_id))
    if model_name == "userprofile":
        return queryset.filter(dealer_id=dealer_id)
    if model_name == settings.AUTH_USER_MODEL.split(".")[-1].lower():
        return queryset.filter(profile__dealer_id=dealer_id)

    return queryset


def _apply_branch_scope(queryset: QuerySet, branch_id: int) -> QuerySet:
    model = queryset.model
    model_name = model._meta.model_name
    fields = _model_field_names(model)

    if "branch" in fields:
        return queryset.filter(branch_id=branch_id)
    if model_name == "branch":
        return queryset.filter(pk=branch_id)
    if "machine" in fields:
        return queryset.filter(machine__branch_id=branch_id)
    if "service_request" in fields:
        return queryset.filter(service_request__branch_id=branch_id)
    if model_name == "dealer":
        return queryset.filter(branches__id=branch_id)
    if model_name == "contact":
        return queryset.filter(branch_id=branch_id)
    if model_name == "userprofile":
        return queryset.filter(branch_id=branch_id)
    if model_name == settings.AUTH_USER_MODEL.split(".")[-1].lower():
        return queryset.filter(profile__branch_id=branch_id)

    return queryset


def _apply_region_scope(queryset: QuerySet, region_id: int) -> QuerySet:
    model = queryset.model
    model_name = model._meta.model_name
    fields = _model_field_names(model)

    if "region" in fields:
        return queryset.filter(region_id=region_id)
    if model_name == "region":
        return queryset.filter(pk=region_id)
    if "machine" in fields:
        return queryset.filter(machine__region_id=region_id)
    if "service_request" in fields:
        return queryset.filter(service_request__region_id=region_id)
    if model_name == "branch":
        return queryset.filter(region_id=region_id)
    if model_name == "userprofile":
        return queryset.filter(region_id=region_id)
    if model_name == settings.AUTH_USER_MODEL.split(".")[-1].lower():
        return queryset.filter(profile__region_id=region_id)

    return queryset


def scope_queryset_to_user(queryset: QuerySet, user) -> QuerySet:
    if not user.is_authenticated:
        return queryset.none()

    if user.is_superuser:
        return queryset

    profile = get_user_profile(user)
    if profile is None:
        return queryset.none()

    organization_id = get_effective_organization_id(user)
    model_name = queryset.model._meta.model_name
    fields = _model_field_names(queryset.model)

    if model_name == "organization":
        return queryset.filter(pk=organization_id) if organization_id else queryset.none()

    if "organization" in fields and organization_id:
        queryset = queryset.filter(organization_id=organization_id)

    if profile.dealer_id:
        queryset = _apply_dealer_scope(queryset, profile.dealer_id)
    if profile.branch_id:
        queryset = _apply_branch_scope(queryset, profile.branch_id)
    if profile.region_id:
        queryset = _apply_region_scope(queryset, profile.region_id)

    return queryset.distinct()


def admin_permission(permission: str) -> Callable[[HttpRequest], bool]:
    def checker(request: HttpRequest) -> bool:
        return request.user.is_authenticated and request.user.has_perm(permission)

    return checker


def admin_environment_badge(request: HttpRequest) -> tuple[str, str]:
    return ("LOCAL", "info") if settings.DEBUG else ("PROD", "warning")


def admin_sidebar_navigation(request: HttpRequest) -> list[dict[str, Any]]:
    return [
        {
            "title": _("Обзор"),
            "separator": True,
            "items": [
                {
                    "title": _("Панель управления"),
                    "icon": "dashboard",
                    "link": reverse("admin:index"),
                    "permission": lambda req: req.user.is_staff,
                },
                {
                    "title": _("Сервисная панель"),
                    "icon": "space_dashboard",
                    "link": reverse("core:dashboard"),
                    "permission": lambda req: req.user.is_authenticated,
                },
                {
                    "title": _("Календарь ТО"),
                    "icon": "event",
                    "link": reverse("core:service_calendar"),
                    "permission": lambda req: req.user.is_authenticated,
                },
            ],
        },
        {
            "title": _("Операции"),
            "items": [
                {
                    "title": _("Очередь заявок"),
                    "icon": "view_list",
                    "link": reverse("core:service_requests"),
                    "permission": lambda req: req.user.is_authenticated,
                },
                {
                    "title": _("Сервисные заявки"),
                    "icon": "support_agent",
                    "link": reverse("admin:service_servicerequest_changelist"),
                    "permission": admin_permission("service.view_servicerequest"),
                },
                {
                    "title": _("Сервисная история"),
                    "icon": "build_circle",
                    "link": reverse("admin:service_servicerecord_changelist"),
                    "permission": admin_permission("service.view_servicerecord"),
                },
                {
                    "title": _("Гарантии"),
                    "icon": "verified_user",
                    "link": reverse("admin:warranties_warranty_changelist"),
                    "permission": admin_permission("warranties.view_warranty"),
                },
            ],
        },
        {
            "title": _("Парк техники"),
            "items": [
                {
                    "title": _("Обзор техники"),
                    "icon": "inventory_2",
                    "link": reverse("core:machine_list"),
                    "permission": lambda req: req.user.is_authenticated,
                },
                {
                    "title": _("Машины"),
                    "icon": "construction",
                    "link": reverse("admin:machines_machine_changelist"),
                    "permission": admin_permission("machines.view_machine"),
                },
                {
                    "title": _("NFC и QR теги"),
                    "icon": "nfc",
                    "link": reverse("admin:machines_machinetag_changelist"),
                    "permission": admin_permission("machines.view_machinetag"),
                },
                {
                    "title": _("Вложения"),
                    "icon": "attach_file",
                    "link": reverse("admin:attachments_attachment_changelist"),
                    "permission": admin_permission("attachments.view_attachment"),
                },
            ],
        },
        {
            "title": _("Структура"),
            "items": [
                {
                    "title": _("Организации"),
                    "icon": "corporate_fare",
                    "link": reverse("admin:organizations_organization_changelist"),
                    "permission": admin_permission("organizations.view_organization"),
                },
                {
                    "title": _("Регионы"),
                    "icon": "map",
                    "link": reverse("admin:branches_region_changelist"),
                    "permission": admin_permission("branches.view_region"),
                },
                {
                    "title": _("Филиалы"),
                    "icon": "apartment",
                    "link": reverse("admin:branches_branch_changelist"),
                    "permission": admin_permission("branches.view_branch"),
                },
                {
                    "title": _("Дилеры"),
                    "icon": "handshake",
                    "link": reverse("admin:dealers_dealer_changelist"),
                    "permission": admin_permission("dealers.view_dealer"),
                },
                {
                    "title": _("Контакты"),
                    "icon": "contact_phone",
                    "link": reverse("admin:dealers_contact_changelist"),
                    "permission": admin_permission("dealers.view_contact"),
                },
            ],
        },
        {
            "title": _("Доступ и контроль"),
            "items": [
                {
                    "title": _("Пользователи"),
                    "icon": "badge",
                    "link": reverse("admin:accounts_user_changelist"),
                    "permission": admin_permission("accounts.view_user"),
                },
                {
                    "title": _("Роли и доступ"),
                    "icon": "manage_accounts",
                    "link": reverse("admin:accounts_userprofile_changelist"),
                    "permission": admin_permission("accounts.view_userprofile"),
                },
                {
                    "title": _("Журнал аудита"),
                    "icon": "policy",
                    "link": reverse("admin:auditlog_auditlog_changelist"),
                    "permission": admin_permission("auditlog.view_auditlog"),
                },
            ],
        },
    ]


def admin_dashboard_callback(
    request: HttpRequest,
    context: dict[str, Any],
) -> dict[str, Any]:
    from apps.machines.models import Machine, MachineTag
    from apps.service.models import ServiceRequest, ServiceRequestStatusChoices
    from apps.warranties.models import Warranty, WarrantyStatusChoices

    today = timezone.localdate()
    service_requests = scope_queryset_to_user(ServiceRequest.objects.all(), request.user)
    machines = scope_queryset_to_user(Machine.objects.all(), request.user)
    warranties = scope_queryset_to_user(Warranty.objects.all(), request.user)

    new_requests = service_requests.filter(status=ServiceRequestStatusChoices.NEW)
    active_requests = service_requests.exclude(
        status__in=[
            ServiceRequestStatusChoices.COMPLETED,
            ServiceRequestStatusChoices.CLOSED,
            ServiceRequestStatusChoices.CANCELLED,
        ]
    )
    in_progress = active_requests.filter(
        status__in=[
            ServiceRequestStatusChoices.TRIAGED,
            ServiceRequestStatusChoices.SCHEDULED,
            ServiceRequestStatusChoices.IN_PROGRESS,
            ServiceRequestStatusChoices.WAITING_PARTS,
        ]
    )
    overdue = active_requests.filter(due_at__lt=timezone.now())
    unassigned_requests = active_requests.filter(
        assigned_manager__isnull=True,
        assigned_engineer__isnull=True,
    )
    upcoming_maintenance = machines.filter(
        next_maintenance_date__isnull=False,
        next_maintenance_date__lte=today + timedelta(days=21),
        next_maintenance_date__gte=today,
        is_active=True,
        is_deleted=False,
    )
    expiring_warranties = warranties.filter(
        status__in=[
            WarrantyStatusChoices.ACTIVE,
            WarrantyStatusChoices.EXPIRING,
        ],
        warranty_end__lte=today + timedelta(days=30),
        warranty_end__gte=today,
    )
    public_without_tag = (
        machines.filter(is_public=True, is_deleted=False)
        .exclude(tags__is_active=True, tags__is_deleted=False)
        .distinct()
    )
    public_pages_preview = [
        {
            "title": item.machine.name,
            "meta": (
                f"{item.machine.serial_number}"
                f"{f' · {item.machine.branch.name}' if item.machine.branch else ''}"
            ),
            "link": f"/m/{item.public_token}/",
        }
        for item in (
            scope_queryset_to_user(
                MachineTag.objects.select_related("machine", "machine__branch"),
                request.user,
            )
            .filter(
                is_active=True,
                is_deleted=False,
                machine__is_deleted=False,
                machine__is_public=True,
            )
            .order_by("machine__name")[:5]
        )
    ]

    context.update(
        {
            "dashboard_cards": [
                {
                    "label": "Новые заявки",
                    "value": new_requests.count(),
                    "caption": "Ожидают обработки",
                    "tone": "primary",
                    "link": (
                        f"{reverse('admin:service_servicerequest_changelist')}"
                        "?status__exact=new"
                    ),
                },
                {
                    "label": "В работе",
                    "value": in_progress.count(),
                    "caption": "Активные заявки",
                    "tone": "info",
                    "link": (
                        f"{reverse('admin:service_servicerequest_changelist')}"
                        "?status__exact=in_progress"
                    ),
                },
                {
                    "label": "Просрочено",
                    "value": overdue.count(),
                    "caption": "Заявки с нарушением срока реакции",
                    "tone": "danger",
                    "link": f"{reverse('admin:service_servicerequest_changelist')}?sla=overdue",
                },
                {
                    "label": "Ближайшее ТО",
                    "value": upcoming_maintenance.count(),
                    "caption": "Машины с обслуживанием в ближайшие 21 день",
                    "tone": "warning",
                    "link": (
                        f"{reverse('admin:machines_machine_changelist')}"
                        "?maintenance_window=upcoming"
                    ),
                },
            ],
            "dashboard_panels": [
                {
                    "title": "Требует внимания",
                    "subtitle": "Заявки и гарантия",
                    "items": [
                        {
                            "title": f"Истекающие гарантии: {expiring_warranties.count()}",
                            "meta": "Ближайшие 30 дней",
                            "link": (
                                f"{reverse('admin:warranties_warranty_changelist')}"
                                "?status__exact=expiring"
                            ),
                        },
                        {
                            "title": f"Без ответственного: {unassigned_requests.count()}",
                            "meta": "Заявки без назначенного ответственного",
                            "link": (
                                f"{reverse('admin:service_servicerequest_changelist')}"
                                "?assigned_manager__isnull=True&assigned_engineer__isnull=True"
                            ),
                        },
                        {
                            "title": f"Публичные страницы без тега: {public_without_tag.count()}",
                            "meta": "Нужна активация или замена QR/NFC",
                            "link": (
                                f"{reverse('admin:machines_machine_changelist')}"
                                "?is_public__exact=1"
                            ),
                        },
                    ],
                },
                {
                    "title": "Последние заявки",
                    "subtitle": "Новые обращения по сервису",
                    "items": [
                        {
                            "title": f"#{item.pk} {item.machine.name}",
                            "meta": f"{item.client_name} · {item.get_status_display()}",
                            "link": reverse("admin:service_servicerequest_change", args=[item.pk]),
                        }
                        for item in (
                            service_requests.select_related("machine")
                            .order_by("-created_at")[:5]
                        )
                    ],
                },
            ],
            "dashboard_quick_links": [
                {
                    "title": "Создать сервисную заявку",
                    "description": "Регистрация нового обращения",
                    "link": reverse("admin:service_servicerequest_add"),
                },
                {
                    "title": "Добавить машину",
                    "description": "Новая карточка машины",
                    "link": reverse("admin:machines_machine_add"),
                },
                {
                    "title": "Обновить гарантию",
                    "description": "Создать или продлить гарантию",
                    "link": reverse("admin:warranties_warranty_add"),
                },
            ],
            "public_pages_preview": public_pages_preview,
        }
    )
    return context


class DeletionStateFilter(admin.SimpleListFilter):
    title = _("Состояние записи")
    parameter_name = "deleted_state"

    def lookups(self, request, model_admin):
        return (
            ("active", _("Активные")),
            ("deleted", _("В архиве")),
            ("all", _("Все")),
        )

    def queryset(self, request, queryset):
        if not hasattr(queryset.model, "is_deleted"):
            return queryset

        value = self.value() or "active"
        if value == "deleted":
            return queryset.filter(is_deleted=True)
        if value == "all":
            return queryset
        return queryset.filter(is_deleted=False)


class ScopeAwareAdmin(ModelAdmin):
    list_filter_submit = True
    list_fullwidth = True
    warn_unsaved_form = True
    compressed_fields = True
    save_on_top = True
    show_full_result_count = False
    empty_value_display = "—"
    actions = (
        "archive_selected",
        "restore_selected",
        "activate_selected",
        "deactivate_selected",
        "publish_selected",
        "hide_selected",
    )

    @admin.action(description="Перевести в архив")
    def archive_selected(self, request: HttpRequest, queryset: QuerySet) -> None:
        if not hasattr(self.model, "is_deleted"):
            self.message_user(
                request,
                "Для этой модели архивирование не используется.",
                messages.WARNING,
            )
            return

        count = queryset.filter(is_deleted=False).update(
            is_deleted=True,
            deleted_at=timezone.now(),
        )
        self.message_user(request, f"Записей переведено в архив: {count}.", messages.SUCCESS)

    @admin.action(description="Восстановить из архива")
    def restore_selected(self, request: HttpRequest, queryset: QuerySet) -> None:
        if not hasattr(self.model, "is_deleted"):
            self.message_user(
                request,
                "Для этой модели восстановление не требуется.",
                messages.WARNING,
            )
            return

        count = queryset.filter(is_deleted=True).update(is_deleted=False, deleted_at=None)
        self.message_user(request, f"Записей восстановлено: {count}.", messages.SUCCESS)

    @admin.action(description="Сделать активными")
    def activate_selected(self, request: HttpRequest, queryset: QuerySet) -> None:
        if not hasattr(self.model, "is_active"):
            self.message_user(request, "Для этой модели нет поля активности.", messages.WARNING)
            return

        count = queryset.update(is_active=True)
        self.message_user(request, f"Активировано записей: {count}.", messages.SUCCESS)

    @admin.action(description="Деактивировать")
    def deactivate_selected(self, request: HttpRequest, queryset: QuerySet) -> None:
        if not hasattr(self.model, "is_active"):
            self.message_user(request, "Для этой модели нет поля активности.", messages.WARNING)
            return

        count = queryset.update(is_active=False)
        self.message_user(request, f"Деактивировано записей: {count}.", messages.SUCCESS)

    @admin.action(description="Открыть публично")
    def publish_selected(self, request: HttpRequest, queryset: QuerySet) -> None:
        field_name = "is_public" if hasattr(self.model, "is_public") else "visibility"
        if field_name == "visibility" and not hasattr(self.model, "visibility"):
            self.message_user(request, "Для этой модели нет публичного режима.", messages.WARNING)
            return

        if field_name == "is_public":
            count = queryset.update(is_public=True)
        else:
            count = queryset.update(visibility="public")
        self.message_user(request, f"Публичных записей обновлено: {count}.", messages.SUCCESS)

    @admin.action(description="Снять с публикации")
    def hide_selected(self, request: HttpRequest, queryset: QuerySet) -> None:
        field_name = "is_public" if hasattr(self.model, "is_public") else "visibility"
        if field_name == "visibility" and not hasattr(self.model, "visibility"):
            self.message_user(request, "Для этой модели нет публичного режима.", messages.WARNING)
            return

        if field_name == "is_public":
            count = queryset.update(is_public=False)
        else:
            count = queryset.update(visibility="internal")
        self.message_user(request, f"Внутренних записей обновлено: {count}.", messages.SUCCESS)

    def get_actions(self, request: HttpRequest):
        actions = super().get_actions(request)

        if not hasattr(self.model, "is_deleted"):
            actions.pop("archive_selected", None)
            actions.pop("restore_selected", None)
        if not hasattr(self.model, "is_active"):
            actions.pop("activate_selected", None)
            actions.pop("deactivate_selected", None)
        if not hasattr(self.model, "is_public") and not hasattr(self.model, "visibility"):
            actions.pop("publish_selected", None)
            actions.pop("hide_selected", None)

        return actions

    def get_queryset(self, request: HttpRequest):
        manager = getattr(self.model, "all_objects", self.model._default_manager)
        queryset = manager.get_queryset()

        list_select_related = self.get_list_select_related(request)
        if list_select_related is True:
            queryset = queryset.select_related()
        elif list_select_related:
            queryset = queryset.select_related(*list_select_related)

        ordering = self.get_ordering(request)
        if ordering:
            queryset = queryset.order_by(*ordering)

        return scope_queryset_to_user(queryset, request.user)

    def get_list_filter(self, request: HttpRequest):
        filters = list(super().get_list_filter(request))
        if hasattr(self.model, "is_deleted") and DeletionStateFilter not in filters:
            filters.append(DeletionStateFilter)
        return filters

    def get_readonly_fields(self, request: HttpRequest, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        for field_name in ("created_at", "updated_at", "deleted_at"):
            if hasattr(self.model, field_name) and field_name not in readonly_fields:
                readonly_fields.append(field_name)
        return readonly_fields

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        queryset = kwargs.get("queryset")
        if queryset is not None:
            kwargs["queryset"] = scope_queryset_to_user(queryset, request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        queryset = kwargs.get("queryset")
        if queryset is not None:
            kwargs["queryset"] = scope_queryset_to_user(queryset, request.user)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def save_model(self, request: HttpRequest, obj, form, change):
        if hasattr(obj, "organization_id") and not obj.organization_id:
            organization_id = get_effective_organization_id(request.user)
            if organization_id:
                obj.organization_id = organization_id
        super().save_model(request, obj, form, change)


class ScopeAwareTabularInline(TabularInline):
    extra = 0
    show_change_link = True

    def get_queryset(self, request: HttpRequest):
        return scope_queryset_to_user(super().get_queryset(request), request.user)


class ScopeAwareStackedInline(StackedInline):
    extra = 0
    show_change_link = True

    def get_queryset(self, request: HttpRequest):
        return scope_queryset_to_user(super().get_queryset(request), request.user)


class ScopeAwareGenericTabularInline(GenericTabularInline):
    extra = 0
    show_change_link = True

    def get_queryset(self, request: HttpRequest):
        return scope_queryset_to_user(super().get_queryset(request), request.user)


def admin_link(obj, *, text: str | None = None) -> str:
    if obj is None:
        return "—"

    url = reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change", args=[obj.pk])
    return format_html(
        '<a href="{}" class="text-primary-700 dark:text-primary-400">{}</a>',
        url,
        text or str(obj),
    )
