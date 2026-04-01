from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from apps.accounts.managers import UserManager
from apps.core.models import TimeStampedModel


class User(AbstractUser):
    email = models.EmailField(_("Email"), unique=True)
    middle_name = models.CharField(_("Отчество"), max_length=150, blank=True)
    position = models.CharField(_("Должность"), max_length=255, blank=True)
    phone = PhoneNumberField(_("Телефон"), blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self) -> str:
        return self.get_full_name() or self.email

    @property
    def role(self) -> str:
        if hasattr(self, "profile"):
            return self.profile.role
        return UserRoleChoices.UNASSIGNED


class UserRoleChoices(models.TextChoices):
    SUPER_ADMIN = "super_admin", _("Супер-администратор")
    DISTRIBUTOR_ADMIN = "distributor_admin", _("Администратор дистрибьютора")
    DEALER_ADMIN = "dealer_admin", _("Администратор дилера")
    SERVICE_MANAGER = "service_manager", _("Сервисный менеджер")
    SERVICE_ENGINEER = "service_engineer", _("Сервисный инженер")
    INTERNAL_OPERATOR = "internal_operator", _("Внутренний оператор")
    UNASSIGNED = "unassigned", _("Не назначено")


class UserProfile(TimeStampedModel):
    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name=_("Пользователь"),
    )
    role = models.CharField(
        _("Роль"),
        max_length=32,
        choices=UserRoleChoices.choices,
        default=UserRoleChoices.UNASSIGNED,
        db_index=True,
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_profiles",
        verbose_name=_("Организация"),
    )
    dealer = models.ForeignKey(
        "dealers.Dealer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_profiles",
        verbose_name=_("Дилер"),
    )
    region = models.ForeignKey(
        "branches.Region",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_profiles",
        verbose_name=_("Регион"),
    )
    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_profiles",
        verbose_name=_("Филиал"),
    )
    notes = models.TextField(_("Внутренняя заметка"), blank=True)

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"
        ordering = ("user__last_name", "user__first_name", "user__email")

    def __str__(self) -> str:
        return f"{self.user} ({self.get_role_display()})"

    def clean(self):
        super().clean()

        if self.role == UserRoleChoices.SUPER_ADMIN:
            if any([self.organization_id, self.dealer_id, self.region_id, self.branch_id]):
                raise ValidationError(
                    _(
                        "Супер-администратор не должен быть ограничен организацией, "
                        "дилером или филиалом."
                    )
                )

        if self.role == UserRoleChoices.DISTRIBUTOR_ADMIN and not self.organization_id:
            raise ValidationError(_("Для администратора дистрибьютора нужно указать организацию."))

        if self.role == UserRoleChoices.DEALER_ADMIN and not self.dealer_id:
            raise ValidationError(_("Для администратора дилера нужно указать дилера."))

        if self.role in {
            UserRoleChoices.SERVICE_MANAGER,
            UserRoleChoices.SERVICE_ENGINEER,
            UserRoleChoices.INTERNAL_OPERATOR,
        } and not any([self.organization_id, self.dealer_id, self.branch_id]):
            raise ValidationError(
                _(
                    "Для сервисных ролей и операторов нужно указать хотя бы "
                    "организацию, дилера или филиал."
                )
            )

        if (
            self.branch_id
            and self.region_id
            and self.branch
            and self.branch.region_id != self.region_id
        ):
            raise ValidationError(_("Филиал должен принадлежать выбранному региону."))

        if (
            self.dealer_id
            and self.organization_id
            and self.dealer
            and self.dealer.organization_id != self.organization_id
        ):
            raise ValidationError(_("Дилер должен принадлежать выбранной организации."))

        if (
            self.branch_id
            and self.organization_id
            and self.branch
            and self.branch.organization_id != self.organization_id
        ):
            raise ValidationError(_("Филиал должен принадлежать выбранной организации."))

        if (
            self.region_id
            and self.organization_id
            and self.region
            and self.region.organization_id != self.organization_id
        ):
            raise ValidationError(_("Регион должен принадлежать выбранной организации."))

    @property
    def scope_summary(self) -> str:
        parts = []
        if self.organization:
            parts.append(self.organization.name)
        if self.dealer:
            parts.append(self.dealer.name)
        if self.region:
            parts.append(self.region.name)
        if self.branch:
            parts.append(self.branch.name)
        return " / ".join(parts) if parts else _("Полный доступ")
