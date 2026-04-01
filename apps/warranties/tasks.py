from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.warranties.models import Warranty, WarrantyStatusChoices


def resolve_warranty_status(warranty: Warranty, today) -> str:
    if warranty.status == WarrantyStatusChoices.VOID:
        return WarrantyStatusChoices.VOID
    if today < warranty.warranty_start:
        return WarrantyStatusChoices.PENDING
    if today > warranty.warranty_end:
        return WarrantyStatusChoices.EXPIRED
    if warranty.warranty_end <= today + timedelta(days=30):
        return WarrantyStatusChoices.EXPIRING
    return WarrantyStatusChoices.ACTIVE


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def sync_warranty_statuses() -> dict[str, int]:
    today = timezone.localdate()
    now = timezone.now()

    checked = 0
    updated = 0
    to_update: list[Warranty] = []

    for warranty in Warranty.all_objects.active().iterator():
        checked += 1
        new_status = resolve_warranty_status(warranty, today)
        if new_status != warranty.status:
            warranty.status = new_status
            warranty.updated_at = now
            to_update.append(warranty)

    if to_update:
        Warranty.all_objects.bulk_update(to_update, ["status", "updated_at"])
        updated = len(to_update)

    return {
        "checked": checked,
        "updated": updated,
    }
