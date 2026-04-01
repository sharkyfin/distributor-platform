FROM python:3.13-slim

ARG APP_ENV=local

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements ./requirements

RUN python -m pip install --upgrade pip \
    && if [ "$APP_ENV" = "production" ]; then \
        pip install -r requirements/production.txt; \
    else \
        pip install -r requirements/local.txt; \
    fi

COPY . .

RUN chmod +x docker/start-web.sh docker/start-celery-worker.sh docker/start-celery-beat.sh

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
