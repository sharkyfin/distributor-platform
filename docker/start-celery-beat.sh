#!/bin/sh
set -e

exec celery -A config beat -l INFO
