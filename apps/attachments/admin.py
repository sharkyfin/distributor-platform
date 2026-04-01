from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RelatedDropdownFilter
from unfold.decorators import display

from apps.attachments.models import (
    Attachment,
    AttachmentFileTypeChoices,
    AttachmentVisibilityChoices,
)
from apps.core.admin import ScopeAwareAdmin, ScopeAwareGenericTabularInline, admin_link


class AttachmentInline(ScopeAwareGenericTabularInline):
    model = Attachment
    ct_field = "content_type"
    ct_fk_field = "object_id"
    fields = (
        "title",
        "file",
        "file_type",
        "visibility",
        "uploaded_by",
        "original_name",
        "size",
    )
    readonly_fields = ("original_name", "size")
    autocomplete_fields = ("organization", "uploaded_by")


@admin.register(Attachment)
class AttachmentAdmin(ScopeAwareAdmin):
    actions = ("archive_selected", "restore_selected", "publish_selected", "hide_selected")
    list_display = (
        "title_or_name",
        "content_object_display",
        "file_type_badge",
        "visibility_badge",
        "organization",
        "uploaded_by",
        "created_at",
        "size_display",
    )
    list_filter = (
        ("organization", RelatedDropdownFilter),
        ("file_type", ChoicesDropdownFilter),
        ("visibility", ChoicesDropdownFilter),
        ("content_type", RelatedDropdownFilter),
    )
    search_fields = ("title", "original_name", "mime_type", "uploaded_by__email")
    ordering = ("-created_at",)
    autocomplete_fields = ("organization", "uploaded_by")
    readonly_fields = (
        "content_object_display",
        "original_name",
        "mime_type",
        "size",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    fieldsets = (
        (
            "Файл",
            {
                "fields": (
                    ("organization", "uploaded_by"),
                    "content_object_display",
                    ("title", "original_name"),
                    "file",
                    ("file_type", "visibility"),
                )
            },
        ),
        ("Метаданные", {"fields": (("mime_type", "size"),)}),
        ("Система", {"classes": ("tab",), "fields": (("created_at", "updated_at"), "deleted_at")}),
    )

    def has_module_permission(self, request):
        profile = getattr(request.user, "profile", None)
        if request.user.is_superuser:
            return True
        if profile and profile.role in {"distributor_admin", "service_manager"}:
            return True
        return request.user.has_perm("attachments.view_attachment")

    @admin.display(description="Файл")
    def title_or_name(self, obj: Attachment) -> str:
        return obj.title or obj.original_name or obj.file.name

    @admin.display(description="Объект")
    def content_object_display(self, obj: Attachment) -> str:
        return admin_link(obj.content_object) if obj.content_object else "—"

    @display(
        description="Тип",
        label={
            AttachmentFileTypeChoices.IMAGE: "info",
            AttachmentFileTypeChoices.PDF: "danger",
            AttachmentFileTypeChoices.DOCUMENT: "primary",
            AttachmentFileTypeChoices.SPREADSHEET: "success",
            AttachmentFileTypeChoices.ARCHIVE: "warning",
            AttachmentFileTypeChoices.OTHER: "default",
        },
    )
    def file_type_badge(self, obj: Attachment):
        return (obj.file_type, obj.get_file_type_display())

    @display(
        description="Видимость",
        label={
            AttachmentVisibilityChoices.PUBLIC: "success",
            AttachmentVisibilityChoices.INTERNAL: "default",
        },
    )
    def visibility_badge(self, obj: Attachment):
        return (obj.visibility, obj.get_visibility_display())

    @admin.display(description="Размер")
    def size_display(self, obj: Attachment) -> str:
        if not obj.size:
            return "—"
        return format_html("{} КБ", round(obj.size / 1024, 1))
