from __future__ import annotations

from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError
from phonenumber_field.formfields import PhoneNumberField

MAX_PUBLIC_UPLOADS = 4
MAX_PUBLIC_UPLOAD_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiImageField(forms.FileField):
    widget = MultiFileInput(
        attrs={
            "accept": ".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp",
        }
    )

    def clean(self, data, initial=None):
        single_clean = super().clean
        if not data:
            return []
        if isinstance(data, (list, tuple)):
            return [single_clean(item, initial) for item in data]
        return [single_clean(data, initial)]


class PublicServiceRequestForm(forms.Form):
    name = forms.CharField(
        label="Ваше имя",
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Например, Иван Петров",
                "autocomplete": "name",
            }
        ),
    )
    phone = PhoneNumberField(
        label="Телефон",
        region="RU",
        widget=forms.TextInput(
            attrs={
                "placeholder": "+7 900 123-45-67",
                "autocomplete": "tel",
            }
        ),
    )
    company = forms.CharField(
        label="Компания",
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "ООО Пример",
                "autocomplete": "organization",
            }
        ),
    )
    problem_description = forms.CharField(
        label="Описание проблемы",
        min_length=20,
        widget=forms.Textarea(
            attrs={
                "rows": 5,
                "placeholder": (
                    "Опишите неисправность, симптомы, когда возникла проблема и нужна "
                    "ли срочная помощь."
                ),
            }
        ),
    )
    photos = MultiImageField(
        label="Фото неисправности",
        required=False,
        help_text=(
            "До 4 изображений. Поддерживаются JPG, PNG и WEBP. Размер одного файла до 5 МБ."
        ),
    )
    consent = forms.BooleanField(
        label="Согласен на обработку персональных данных для обратной связи по сервисной заявке",
        error_messages={
            "required": "Без согласия заявка не может быть отправлена.",
        },
    )

    def clean_problem_description(self) -> str:
        value = self.cleaned_data["problem_description"].strip()
        if len(value.split()) < 3:
            raise ValidationError(
                "Опишите проблему чуть подробнее, чтобы сервисная команда могла быстрее помочь."
            )
        return value

    def clean_photos(self):
        files = self.files.getlist("photos")

        if len(files) > MAX_PUBLIC_UPLOADS:
            raise ValidationError(f"Можно приложить не более {MAX_PUBLIC_UPLOADS} файлов.")

        validated_files = []
        for uploaded_file in files:
            extension = Path(uploaded_file.name).suffix.lower()
            content_type = getattr(uploaded_file, "content_type", "")

            if extension not in ALLOWED_IMAGE_EXTENSIONS:
                raise ValidationError(
                    "Разрешены только изображения JPG, PNG или WEBP."
                )

            if content_type and content_type not in ALLOWED_IMAGE_MIME_TYPES:
                raise ValidationError(
                    "Загружайте только изображения JPG, PNG или WEBP."
                )

            if uploaded_file.size > MAX_PUBLIC_UPLOAD_SIZE:
                raise ValidationError(
                    "Один из файлов превышает лимит 5 МБ."
                )

            validated_files.append(uploaded_file)

        return validated_files

    def build_service_request_data(self) -> dict[str, object]:
        return {
            "client_name": self.cleaned_data["name"].strip(),
            "client_phone": self.cleaned_data["phone"],
            "client_company": self.cleaned_data["company"].strip(),
            "problem_description": self.cleaned_data["problem_description"].strip(),
            "consent_to_processing": self.cleaned_data["consent"],
        }
