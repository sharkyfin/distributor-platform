# Цифровой сервисный паспорт спецтехники

Django 5.2 monolith для сервисного сопровождения спецтехники: публичные страницы машин по QR/NFC, внутренняя очередь обращений, гарантия, история обслуживания и административная панель на Unfold.

## Возможности

- публичные страницы: `/`, `/about/`, `/contact/`, `/m/<public_token>/`, `/m/<public_token>/request/`
- внутренние страницы: `/dashboard/`, `/machines/`, `/machines/<id>/`, `/service-requests/`, `/service-calendar/`
- Django Admin + Unfold с кастомной навигацией и дашбордом
- кастомная модель пользователя, роли и разграничение доступа
- разделение публичных и внутренних данных
- Celery + Redis для фоновых задач
- локальное файловое хранилище и S3-compatible backend
- Docker Compose для локального запуска
- команда загрузки базового набора данных и базовые интеграционные тесты

## Стек

- Python 3.13
- Django 5.2
- PostgreSQL
- Redis
- Celery
- Django REST Framework
- HTMX
- Tailwind tooling
- Unfold Admin

## Структура проекта

```text
apps/
  accounts/       пользователи, роли, права доступа
  attachments/    вложения
  auditlog/       журнал изменений
  branches/       регионы и филиалы
  core/           общие утилиты, внутренние страницы, seed-команда
  dealers/        дилеры и контакты
  machines/       техника, теги, публичные страницы машин
  organizations/  организации
  public_pages/   публичные страницы и формы
  service/        заявки и сервисная история
  warranties/     гарантии
config/
  settings/
    base.py
    local.py
    production.py
    test.py
```

## Локальный запуск

1. Создайте виртуальное окружение и установите зависимости:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements/local.txt
```

2. Подготовьте `.env`:

```bash
cp .env.example .env
```

3. Поднимите инфраструктуру:

```bash
docker compose up -d db redis mailpit
```

4. Примените миграции:

```bash
python manage.py migrate
```

5. Загрузите базовые данные:

```bash
python manage.py seed_reference_data --password ServicePass123!
```

6. Запустите Django:

```bash
python manage.py runserver
```

## Запуск через Docker Compose

Полный стек:

```bash
docker compose up --build
```

После первого старта загрузите базовые данные:

```bash
docker compose exec web python manage.py seed_reference_data --password ServicePass123!
```

Доступные сервисы:

- приложение: `http://127.0.0.1:8000`
- админ-панель: `http://127.0.0.1:8000/admin/`
- Mailpit: `http://127.0.0.1:8025`

## Служебные учетные записи

Команда `seed_reference_data` создает пользователей с одинаковым паролем, который передан через `--password`.

- `superadmin@atlas-machinery.ru` — Super Admin
- `distributor.admin@atlas-machinery.ru` — Distributor Admin
- `dealer.admin@atlas-machinery.ru` — Dealer Admin
- `service.manager@atlas-machinery.ru` — Service Manager
- `service.engineer@atlas-machinery.ru` — Service Engineer
- `operator@atlas-machinery.ru` — Internal Operator

## Базовый набор данных

Команда `seed_reference_data` создает:

- 1 организацию
- 3 региона
- 5 филиалов
- 3 дилера
- 20 машин
- 20 активных тегов
- 20 гарантий
- 18 сервисных заявок
- 24 сервисные записи
- публичные контакты и документы

Для пересоздания набора:

```bash
python manage.py seed_reference_data --reset --password ServicePass123!
```

## Тесты

Используется отдельный `config.settings.test` на SQLite и локальном `MEDIA_ROOT`.

Запуск:

```bash
pytest -q
```

Что проверяется:

- публичная заявка со страницы машины создает внутренний `ServiceRequest`
- внутренние страницы соблюдают разграничение доступа по роли
- команда загрузки данных создает ожидаемый набор записей

## Celery и фоновые задачи

Локально `worker` и `beat` поднимаются через `docker compose`.

Основные periodic tasks:

- синхронизация статусов гарантий
- обновление дат технического обслуживания

Ручной запуск вне Docker:

```bash
celery -A config worker -l INFO
celery -A config beat -l INFO
```

## Storage

По умолчанию локальная среда использует `MEDIA_ROOT`.

Для S3-compatible storage укажите в `.env`:

- `USE_S3_STORAGE=True`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_STORAGE_BUCKET_NAME`
- `AWS_S3_ENDPOINT_URL`

Проект рассчитан на разворачивание в собственной инфраструктуре без обязательной зависимости от внешних SaaS.

## Полезные команды

```bash
python manage.py createsuperuser
python manage.py seed_reference_data --reset
python manage.py check
pytest -q
ruff check config apps tests
docker compose up --build
```
