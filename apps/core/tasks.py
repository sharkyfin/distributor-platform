from __future__ import annotations

from celery import shared_task
from django.utils import timezone


@shared_task(ignore_result=False)
def infrastructure_ping() -> dict[str, str]:
    return {
        "status": "ok",
        "timestamp": timezone.now().isoformat(),
    }
