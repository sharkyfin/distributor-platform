from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("service_passport")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.set_default()
app.autodiscover_tasks(
    [
        "apps.core",
        "apps.machines",
        "apps.warranties",
    ]
)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
