from __future__ import annotations

from collections.abc import Iterable
from datetime import timedelta
from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, QuerySet
from django.http import Http404
from django.urls import reverse
from django.utils import timezone
from django.views.generic import DetailView, ListView, TemplateView

from apps.accounts.models import UserRoleChoices
from apps.attachments.models import Attachment
from apps.branches.models import Branch, Region
from apps.core.admin import scope_queryset_to_user
from apps.dealers.models import Dealer
from apps.machines.models import Machine, MachineStatusChoices
from apps.service.models import (
    ServiceRequest,
    ServiceRequestPriorityChoices,
    ServiceRequestStatusChoices,
)
from apps.warranties.models import WarrantyStatusChoices

CLOSED_REQUEST_STATUSES = {
    ServiceRequestStatusChoices.COMPLETED,
    ServiceRequestStatusChoices.CLOSED,
    ServiceRequestStatusChoices.CANCELLED,
}


def _to_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _ratio_rows(rows: Iterable[dict[str, Any]], count_key: str = "total") -> list[dict[str, Any]]:
    prepared_rows = list(rows)
    max_value = max((row[count_key] for row in prepared_rows), default=0)

    for row in prepared_rows:
        row["ratio"] = int((row[count_key] / max_value) * 100) if max_value else 0

    return prepared_rows


class InternalAccessMixin(LoginRequiredMixin):
    login_url = "admin:login"
    nav_key = ""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not self.has_internal_access():
            raise PermissionDenied("Недостаточно прав доступа.")
        return super().dispatch(request, *args, **kwargs)

    def has_internal_access(self) -> bool:
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True

        profile = getattr(user, "profile", None)
        return bool(profile and profile.role != UserRoleChoices.UNASSIGNED)

    def get_internal_navigation(self) -> list[dict[str, str]]:
        return [
            {
                "key": "dashboard",
                "label": "Сервисная панель",
                "href": reverse("core:dashboard"),
                "meta": "Заявки и сроки",
            },
            {
                "key": "service_requests",
                "label": "Сервисные заявки",
                "href": reverse("core:service_requests"),
                "meta": "Реестр заявок",
            },
            {
                "key": "machines",
                "label": "Парк техники",
                "href": reverse("core:machine_list"),
                "meta": "Карточки техники",
            },
            {
                "key": "service_calendar",
                "label": "Календарь ТО",
                "href": reverse("core:service_calendar"),
                "meta": "План обслуживания",
            },
        ]

    def get_querystring(self, *, exclude: Iterable[str] = ()) -> str:
        querydict = self.request.GET.copy()
        for key in exclude:
            querydict.pop(key, None)
        return querydict.urlencode()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "current_nav": self.nav_key,
                "internal_navigation": self.get_internal_navigation(),
                "querystring_without_page": self.get_querystring(exclude=("page",)),
            }
        )
        return context


class ScopedMachineMixin(InternalAccessMixin):
    def get_machine_base_queryset(self) -> QuerySet[Machine]:
        queryset = (
            Machine.objects.select_related("organization", "region", "branch", "dealer")
            .annotate(
                open_requests_count=Count(
                    "service_requests",
                    filter=(
                        ~Q(service_requests__status__in=CLOSED_REQUEST_STATUSES)
                        & Q(service_requests__is_deleted=False)
                    ),
                    distinct=True,
                ),
                active_tag_count=Count(
                    "tags",
                    filter=Q(tags__is_active=True, tags__is_deleted=False),
                    distinct=True,
                ),
            )
            .order_by("name", "serial_number")
        )
        return scope_queryset_to_user(queryset, self.request.user).filter(is_deleted=False)

    def filter_machine_queryset(self, queryset: QuerySet[Machine]) -> QuerySet[Machine]:
        search = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()
        region_id = _to_int(self.request.GET.get("region"))
        branch_id = _to_int(self.request.GET.get("branch"))
        dealer_id = _to_int(self.request.GET.get("dealer"))
        public_state = self.request.GET.get("public_state", "").strip()

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(model_name__icontains=search)
                | Q(serial_number__icontains=search)
                | Q(inventory_number__icontains=search)
            )
        if status:
            queryset = queryset.filter(status=status)
        if region_id:
            queryset = queryset.filter(region_id=region_id)
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        if dealer_id:
            queryset = queryset.filter(dealer_id=dealer_id)
        if public_state == "public":
            queryset = queryset.filter(is_public=True)
        elif public_state == "private":
            queryset = queryset.filter(is_public=False)

        return queryset


class ScopedServiceRequestMixin(InternalAccessMixin):
    def get_service_request_base_queryset(self) -> QuerySet[ServiceRequest]:
        queryset = (
            ServiceRequest.objects.select_related(
                "machine",
                "dealer",
                "region",
                "branch",
                "assigned_manager",
                "assigned_engineer",
            )
            .order_by("due_at", "-created_at")
        )
        return scope_queryset_to_user(queryset, self.request.user).filter(is_deleted=False)

    def filter_service_request_queryset(
        self,
        queryset: QuerySet[ServiceRequest],
    ) -> QuerySet[ServiceRequest]:
        search = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()
        priority = self.request.GET.get("priority", "").strip()
        region_id = _to_int(self.request.GET.get("region"))
        branch_id = _to_int(self.request.GET.get("branch"))
        bucket = self.request.GET.get("bucket", "").strip()

        if search:
            queryset = queryset.filter(
                Q(machine__name__icontains=search)
                | Q(machine__serial_number__icontains=search)
                | Q(client_name__icontains=search)
                | Q(client_company__icontains=search)
                | Q(problem_description__icontains=search)
            )
        if status:
            queryset = queryset.filter(status=status)
        if priority:
            queryset = queryset.filter(priority=priority)
        if region_id:
            queryset = queryset.filter(region_id=region_id)
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)

        if bucket == "new":
            queryset = queryset.filter(status=ServiceRequestStatusChoices.NEW)
        elif bucket == "in_progress":
            queryset = queryset.filter(
                status__in=[
                    ServiceRequestStatusChoices.TRIAGED,
                    ServiceRequestStatusChoices.SCHEDULED,
                    ServiceRequestStatusChoices.IN_PROGRESS,
                    ServiceRequestStatusChoices.WAITING_PARTS,
                ]
            )
        elif bucket == "overdue":
            queryset = queryset.exclude(status__in=CLOSED_REQUEST_STATUSES).filter(
                due_at__lt=timezone.now()
            )
        elif bucket == "high_priority":
            queryset = queryset.exclude(status__in=CLOSED_REQUEST_STATUSES).filter(
                priority__in=[
                    ServiceRequestPriorityChoices.HIGH,
                    ServiceRequestPriorityChoices.CRITICAL,
                ]
            )

        return queryset


class DashboardView(ScopedServiceRequestMixin, ScopedMachineMixin, TemplateView):
    template_name = "internal/dashboard.html"
    nav_key = "dashboard"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        today = timezone.localdate()

        base_requests = self.get_service_request_base_queryset()
        filtered_requests = self.filter_service_request_queryset(base_requests)

        machine_queryset = self.filter_machine_queryset(self.get_machine_base_queryset())
        if region_id := _to_int(self.request.GET.get("region")):
            machine_queryset = machine_queryset.filter(region_id=region_id)
        if branch_id := _to_int(self.request.GET.get("branch")):
            machine_queryset = machine_queryset.filter(branch_id=branch_id)

        active_requests = filtered_requests.exclude(status__in=CLOSED_REQUEST_STATUSES)
        overdue_requests = active_requests.filter(due_at__lt=now)
        upcoming_maintenance = machine_queryset.filter(
            next_maintenance_date__isnull=False,
            next_maintenance_date__gte=today,
            next_maintenance_date__lte=today + timedelta(days=30),
            is_active=True,
        )

        status_choices = dict(ServiceRequestStatusChoices.choices)
        status_breakdown = _ratio_rows(
            [
                {
                    "label": status_choices.get(item["status"], item["status"]),
                    "slug": item["status"],
                    "total": item["total"],
                }
                for item in filtered_requests.values("status")
                .annotate(total=Count("id"))
                .order_by("-total", "status")
            ]
        )
        region_breakdown = _ratio_rows(
            [
                {
                    "label": item["region__name"] or "Без региона",
                    "total": item["total"],
                }
                for item in filtered_requests.values("region__name")
                .annotate(total=Count("id"))
                .order_by("-total", "region__name")
            ]
        )

        active_total = active_requests.count()
        overdue_total = overdue_requests.count()
        sla_health = (
            int(((active_total - overdue_total) / active_total) * 100)
            if active_total
            else 100
        )

        regions = (
            Region.objects.filter(service_requests__in=base_requests)
            .distinct()
            .order_by("ordering", "name")
        )
        branches = (
            Branch.objects.filter(service_requests__in=base_requests)
            .distinct()
            .order_by("region__ordering", "name")
        )

        context.update(
            {
                "page_title": "Панель сервиса",
                "page_subtitle": "Текущие заявки, сроки реакции и ближайшее обслуживание.",
                "dashboard_cards": [
                    {
                        "label": "Новые",
                        "value": filtered_requests.filter(
                            status=ServiceRequestStatusChoices.NEW
                        ).count(),
                        "tone": "primary",
                        "caption": "Требуют обработки",
                    },
                    {
                        "label": "В работе",
                        "value": filtered_requests.filter(
                            status__in=[
                                ServiceRequestStatusChoices.TRIAGED,
                                ServiceRequestStatusChoices.SCHEDULED,
                                ServiceRequestStatusChoices.IN_PROGRESS,
                                ServiceRequestStatusChoices.WAITING_PARTS,
                            ]
                        ).count(),
                        "tone": "info",
                        "caption": "Открытые заявки",
                    },
                    {
                        "label": "Просрочено",
                        "value": overdue_total,
                        "tone": "danger",
                        "caption": "Нарушен срок реакции",
                    },
                    {
                        "label": "В срок",
                        "value": f"{sla_health}%",
                        "tone": "success",
                        "caption": "Доля активных заявок без просрочки",
                    },
                ],
                "queue_preview": filtered_requests[:8],
                "upcoming_maintenance_preview": upcoming_maintenance[:8],
                "status_breakdown": status_breakdown,
                "region_breakdown": region_breakdown,
                "filter_regions": regions,
                "filter_branches": branches,
                "selected_region": self.request.GET.get("region", ""),
                "selected_branch": self.request.GET.get("branch", ""),
                "selected_bucket": self.request.GET.get("bucket", "all") or "all",
                "filters_applied": bool(
                    self.request.GET.get("region")
                    or self.request.GET.get("branch")
                    or self.request.GET.get("bucket")
                ),
            }
        )
        return context


class MachineListView(ScopedMachineMixin, ListView):
    template_name = "internal/machine_list.html"
    context_object_name = "machines"
    paginate_by = 18
    nav_key = "machines"

    def get_queryset(self):
        queryset = self.get_machine_base_queryset()
        return self.filter_machine_queryset(queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_queryset = self.get_machine_base_queryset()
        filtered_queryset = self.object_list
        today = timezone.localdate()

        context.update(
            {
                "page_title": "Парк техники",
                "page_subtitle": "Машины, статус публикации и плановое обслуживание.",
                "filter_regions": (
                    Region.objects.filter(machines__in=base_queryset)
                    .distinct()
                    .order_by("ordering", "name")
                ),
                "filter_branches": (
                    Branch.objects.filter(machines__in=base_queryset)
                    .distinct()
                    .order_by("region__ordering", "name")
                ),
                "filter_dealers": (
                    Dealer.objects.filter(machines__in=base_queryset)
                    .distinct()
                    .order_by("name")
                ),
                "machine_statuses": MachineStatusChoices.choices,
                "selected_filters": {
                    "q": self.request.GET.get("q", "").strip(),
                    "status": self.request.GET.get("status", ""),
                    "region": self.request.GET.get("region", ""),
                    "branch": self.request.GET.get("branch", ""),
                    "dealer": self.request.GET.get("dealer", ""),
                    "public_state": self.request.GET.get("public_state", ""),
                },
                "machine_cards": [
                    {
                        "label": "Всего в выборке",
                        "value": filtered_queryset.count(),
                        "tone": "neutral",
                    },
                    {
                        "label": "Публичные страницы",
                        "value": filtered_queryset.filter(is_public=True).count(),
                        "tone": "primary",
                    },
                    {
                        "label": "Без активного тега",
                        "value": filtered_queryset.filter(
                            is_public=True,
                            active_tag_count=0,
                        ).count(),
                        "tone": "warning",
                    },
                    {
                        "label": "ТО в 30 дней",
                        "value": filtered_queryset.filter(
                            next_maintenance_date__isnull=False,
                            next_maintenance_date__gte=today,
                            next_maintenance_date__lte=today + timedelta(days=30),
                        ).count(),
                        "tone": "info",
                    },
                ],
            }
        )
        return context


class MachineDetailView(InternalAccessMixin, DetailView):
    template_name = "internal/machine_detail.html"
    context_object_name = "machine"
    nav_key = "machines"

    def get_queryset(self):
        queryset = Machine.objects.select_related(
            "organization",
            "region",
            "branch",
            "dealer",
        ).order_by("name")
        return scope_queryset_to_user(queryset, self.request.user).filter(is_deleted=False)

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()
        try:
            return queryset.get(pk=self.kwargs["pk"])
        except Machine.DoesNotExist as exc:
            raise Http404("Машина не найдена.") from exc

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        machine = self.object
        current_warranty = machine.current_warranty
        all_warranties = list(machine.warranties.order_by("-warranty_end")[:5])
        if current_warranty is None and all_warranties:
            current_warranty = all_warranties[0]

        service_records = list(
            machine.service_records.select_related("engineer", "branch")
            .order_by("-service_date", "-created_at")[:8]
        )
        service_requests = list(
            machine.service_requests.select_related(
                "assigned_manager",
                "assigned_engineer",
                "branch",
                "region",
                "dealer",
            ).order_by("-created_at")[:8]
        )
        attachments = list(
            Attachment.objects.filter(
                Q(machine=machine)
                | Q(service_record__machine=machine)
                | Q(service_request__machine=machine)
            )
            .select_related("uploaded_by", "content_type")
            .distinct()
            .order_by("-created_at")[:10]
        )

        active_tag = machine.active_tag
        public_passport_url = None
        if machine.is_public and active_tag:
            public_passport_url = reverse(
                "public_pages:machine_detail",
                args=[active_tag.public_token],
            )

        open_request_count = machine.service_requests.exclude(
            status__in=CLOSED_REQUEST_STATUSES
        ).count()
        request_user = self.request.user
        admin_actions = []

        if request_user.is_staff and request_user.has_perm("machines.change_machine"):
            admin_actions.append(
                {
                    "label": "Редактировать машину",
                    "href": reverse("admin:machines_machine_change", args=[machine.pk]),
                }
            )
        if request_user.is_staff and request_user.has_perm("service.add_servicerecord"):
            admin_actions.append(
                {
                    "label": "Добавить сервисную запись",
                    "href": f"{reverse('admin:service_servicerecord_add')}?machine={machine.pk}",
                }
            )
        if request_user.is_staff and request_user.has_perm("service.add_servicerequest"):
            admin_actions.append(
                {
                    "label": "Создать сервисную заявку",
                    "href": f"{reverse('admin:service_servicerequest_add')}?machine={machine.pk}",
                }
            )

        context.update(
            {
                "page_title": machine.name,
                "page_subtitle": (
                    "Гарантия, сервисная история и последние обращения по машине."
                ),
                "current_warranty": current_warranty,
                "warranty_statuses": WarrantyStatusChoices,
                "warranties": all_warranties,
                "service_records": service_records,
                "service_requests": service_requests,
                "attachments": attachments,
                "active_tag": active_tag,
                "public_passport_url": public_passport_url,
                "open_request_count": open_request_count,
                "admin_actions": admin_actions,
                "machine_detail_cards": [
                    {
                        "label": "Статус машины",
                        "value": machine.get_status_display(),
                        "tone": machine.status,
                    },
                    {
                        "label": "Открытые заявки",
                        "value": open_request_count,
                        "tone": "danger" if open_request_count else "success",
                    },
                    {
                        "label": "Последнее ТО",
                        "value": (
                            machine.last_maintenance_date.strftime("%d.%m.%Y")
                            if machine.last_maintenance_date
                            else "Не указано"
                        ),
                        "tone": "neutral",
                    },
                    {
                        "label": "Следующее ТО",
                        "value": (
                            machine.next_maintenance_date.strftime("%d.%m.%Y")
                            if machine.next_maintenance_date
                            else "Не назначено"
                        ),
                        "tone": "warning",
                    },
                ],
            }
        )
        return context


class ServiceRequestListView(ScopedServiceRequestMixin, ListView):
    template_name = "internal/service_request_list.html"
    context_object_name = "service_requests"
    paginate_by = 20
    nav_key = "service_requests"

    def get_queryset(self):
        queryset = self.get_service_request_base_queryset()
        return self.filter_service_request_queryset(queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_queryset = self.get_service_request_base_queryset()
        filtered_queryset = self.object_list
        overdue_count = filtered_queryset.exclude(status__in=CLOSED_REQUEST_STATUSES).filter(
            due_at__lt=timezone.now()
        ).count()

        context.update(
            {
                "page_title": "Сервисные заявки",
                "page_subtitle": "Реестр обращений с фильтрами по статусу, приоритету и локации.",
                "request_cards": [
                    {
                        "label": "Новые",
                        "value": filtered_queryset.filter(
                            status=ServiceRequestStatusChoices.NEW
                        ).count(),
                        "tone": "primary",
                    },
                    {
                        "label": "В работе",
                        "value": filtered_queryset.filter(
                            status__in=[
                                ServiceRequestStatusChoices.TRIAGED,
                                ServiceRequestStatusChoices.SCHEDULED,
                                ServiceRequestStatusChoices.IN_PROGRESS,
                                ServiceRequestStatusChoices.WAITING_PARTS,
                            ]
                        ).count(),
                        "tone": "info",
                    },
                    {
                        "label": "Просрочено",
                        "value": overdue_count,
                        "tone": "danger",
                    },
                    {
                        "label": "Критичные",
                        "value": filtered_queryset.filter(
                            priority=ServiceRequestPriorityChoices.CRITICAL
                        ).count(),
                        "tone": "warning",
                    },
                ],
                "filter_regions": (
                    Region.objects.filter(service_requests__in=base_queryset)
                    .distinct()
                    .order_by("ordering", "name")
                ),
                "filter_branches": (
                    Branch.objects.filter(service_requests__in=base_queryset)
                    .distinct()
                    .order_by("region__ordering", "name")
                ),
                "request_statuses": ServiceRequestStatusChoices.choices,
                "request_priorities": ServiceRequestPriorityChoices.choices,
                "selected_filters": {
                    "q": self.request.GET.get("q", "").strip(),
                    "status": self.request.GET.get("status", ""),
                    "priority": self.request.GET.get("priority", ""),
                    "region": self.request.GET.get("region", ""),
                    "branch": self.request.GET.get("branch", ""),
                    "bucket": self.request.GET.get("bucket", ""),
                },
            }
        )
        return context


class ServiceCalendarView(ScopedMachineMixin, ListView):
    template_name = "internal/service_calendar.html"
    context_object_name = "machines"
    paginate_by = 24
    nav_key = "service_calendar"

    def get_queryset(self):
        queryset = self.filter_machine_queryset(self.get_machine_base_queryset())
        today = timezone.localdate()
        window_days = _to_int(self.request.GET.get("window")) or 30

        if self.request.GET.get("mode") == "overdue":
            queryset = queryset.filter(
                next_maintenance_date__isnull=False,
                next_maintenance_date__lt=today,
            )
        else:
            queryset = queryset.filter(
                next_maintenance_date__isnull=False,
                next_maintenance_date__lte=today + timedelta(days=window_days),
            )
        return queryset.order_by("next_maintenance_date", "name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_queryset = self.filter_machine_queryset(self.get_machine_base_queryset())
        today = timezone.localdate()
        window_days = _to_int(self.request.GET.get("window")) or 30

        context.update(
            {
                "page_title": "Календарь обслуживания",
                "page_subtitle": "Ближайшее и просроченное техническое обслуживание.",
                "filter_regions": (
                    Region.objects.filter(machines__in=base_queryset)
                    .distinct()
                    .order_by("ordering", "name")
                ),
                "filter_branches": (
                    Branch.objects.filter(machines__in=base_queryset)
                    .distinct()
                    .order_by("region__ordering", "name")
                ),
                "filter_dealers": (
                    Dealer.objects.filter(machines__in=base_queryset)
                    .distinct()
                    .order_by("name")
                ),
                "selected_filters": {
                    "q": self.request.GET.get("q", "").strip(),
                    "region": self.request.GET.get("region", ""),
                    "branch": self.request.GET.get("branch", ""),
                    "dealer": self.request.GET.get("dealer", ""),
                    "status": self.request.GET.get("status", ""),
                    "public_state": self.request.GET.get("public_state", ""),
                    "window": str(window_days),
                    "mode": self.request.GET.get("mode", "window") or "window",
                },
                "calendar_cards": [
                    {
                        "label": "Просрочено ТО",
                        "value": base_queryset.filter(
                            next_maintenance_date__isnull=False,
                            next_maintenance_date__lt=today,
                        ).count(),
                        "tone": "danger",
                    },
                    {
                        "label": "ТО в 7 дней",
                        "value": base_queryset.filter(
                            next_maintenance_date__isnull=False,
                            next_maintenance_date__gte=today,
                            next_maintenance_date__lte=today + timedelta(days=7),
                        ).count(),
                        "tone": "warning",
                    },
                    {
                        "label": f"ТО в {window_days} дней",
                        "value": base_queryset.filter(
                            next_maintenance_date__isnull=False,
                            next_maintenance_date__gte=today,
                            next_maintenance_date__lte=today + timedelta(days=window_days),
                        ).count(),
                        "tone": "info",
                    },
                    {
                        "label": "Публичные машины",
                        "value": base_queryset.filter(is_public=True).count(),
                        "tone": "primary",
                    },
                ],
                "window_options": [7, 14, 30, 60, 90],
                "today": today,
            }
        )
        return context
