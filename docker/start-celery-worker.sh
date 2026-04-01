#!/bin/sh
set -e

exec celery -A config worker -l INFO --concurrency="${CELERY_WORKER_CONCURRENCY:-2}"
