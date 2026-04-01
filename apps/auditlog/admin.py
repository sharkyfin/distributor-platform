from __future__ import annotations

import json

from django.contrib import admin
from django.utils.html import format_html
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RangeDateTimeFilter,
    RelatedDropdownFilter,
)
from unfold.decorators import display

from apps.auditlog.models import AuditActionChoices, AuditLog
from apps.core.admin import ScopeAwareAdmin


@admin.register(AuditLog)
class AuditLogAdmin(ScopeAwareAdmin):
    actions = ()
    list_display = (
        "timestamp",
        "action_badge",
        "model_name",
        "object_repr",
        "user",
        "organization",
        "summary",
    )
    list_filter = (
        ("organization", RelatedDropdownFilter),
        ("action", ChoicesDropdownFilter),
        ("timestamp", RangeDateTimeFilter),
    )
    search_fields = ("summary", "model_name", "object_id", "object_repr", "user__email")
    ordering = ("-timestamp",)
    readonly_fields = (
        "organization",
        "user",
        "action_badge",
        "model_name",
        "object_id",
        "object_repr",
        "summary",
        "pretty_payload",
        "timestamp",
    )
    fieldsets = (
        (
            "Событие",
            {
                "fields": (
                    ("organization", "user"),
                    ("action_badge", "timestamp"),
                    ("model_name", "object_id"),
                    "object_repr",
                    "summary",
                )
            },
        ),
        ("Payload", {"fields": ("pretty_payload",)}),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @display(
        description="Действие",
        label={
            AuditActionChoices.CREATED: "success",
            AuditActionChoices.UPDATED: "primary",
            AuditActionChoices.DELETED: "danger",
            AuditActionChoices.STATUS_CHANGED: "warning",
            AuditActionChoices.ASSIGNED: "info",
            AuditActionChoices.LOGIN: "default",
            AuditActionChoices.PUBLIC_REQUEST_CREATED: "success",
            AuditActionChoices.EXPORT: "warning",
        },
    )
    def action_badge(self, obj: AuditLog):
        return (obj.action, obj.get_action_display())

    @admin.display(description="Payload")
    def pretty_payload(self, obj: AuditLog) -> str:
        return format_html(
            "<pre class='whitespace-pre-wrap text-xs'>{}</pre>",
            json.dumps(obj.payload, ensure_ascii=False, indent=2),
        )
