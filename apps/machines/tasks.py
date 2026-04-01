from __future__ import annotations

from celery import shared_task

from apps.machines.models import Machine


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def refresh_machine_maintenance_snapshots() -> dict[str, int]:
    inspected = 0
    updated = 0

    for machine in Machine.all_objects.active().iterator():
        inspected += 1
        previous_last = machine.last_maintenance_date
        previous_next = machine.next_maintenance_date

        machine.refresh_maintenance_snapshot(save=False)

        if (
            previous_last != machine.last_maintenance_date
            or previous_next != machine.next_maintenance_date
        ):
            machine.save(
                update_fields=[
                    "last_maintenance_date",
                    "next_maintenance_date",
                    "updated_at",
                ]
            )
            updated += 1

    return {
        "inspected": inspected,
        "updated": updated,
    }
