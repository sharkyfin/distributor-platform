from __future__ import annotations

from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import (
    User,
    UserProfile,
    UserRoleChoices,
)

ROLE_GROUP_NAMES = [
    UserRoleChoices.SUPER_ADMIN,
    UserRoleChoices.DISTRIBUTOR_ADMIN,
    UserRoleChoices.DEALER_ADMIN,
    UserRoleChoices.SERVICE_MANAGER,
    UserRoleChoices.SERVICE_ENGINEER,
    UserRoleChoices.INTERNAL_OPERATOR,
]


@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance: User, created: bool, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
        return

    UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=UserProfile)
def sync_role_group(sender, instance: UserProfile, **kwargs):
    user = instance.user

    managed_groups = []
    for name in ROLE_GROUP_NAMES:
        group, _ = Group.objects.get_or_create(name=name)
        managed_groups.append(group)

    existing_managed_groups = [group for group in managed_groups if group in user.groups.all()]
    if existing_managed_groups:
        user.groups.remove(*existing_managed_groups)

    if instance.role != UserRoleChoices.UNASSIGNED:
        target_group = next(group for group in managed_groups if group.name == instance.role)
        user.groups.add(target_group)

    should_be_staff = user.is_superuser or instance.role != UserRoleChoices.UNASSIGNED
    if user.is_staff != should_be_staff:
        user.is_staff = should_be_staff
        user.save(update_fields=["is_staff"])
