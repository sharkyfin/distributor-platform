# Цифровой сервисный паспорт спецтехники

## Структура проекта

```text
platform/
├── apps/
│   ├── accounts/         # кастомный пользователь, роли, scope-доступ
│   ├── attachments/      # вложения и правила публичности
│   ├── auditlog/         # аудит действий и журнал изменений
│   ├── branches/         # регионы и филиалы
│   ├── core/             # общие миксины, базовые абстракции, internal pages
│   ├── dealers/          # дилеры и публичные сервисные контакты
│   ├── machines/         # техника, теги, публичный паспорт
│   ├── organizations/    # дистрибьюторы и мультиорганизационная изоляция
│   ├── public_pages/     # публичные страницы, machine page, формы заявок
│   ├── service/          # заявки, сервисная очередь, SLA, таймлайн работ
│   └── warranties/       # гарантии и статусы покрытия
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   └── production.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── docs/
├── requirements/
├── static/
│   └── src/              # Tailwind source
├── templates/            # project-level templates и future Unfold overrides
├── manage.py
├── package.json
└── pyproject.toml
```

## Архитектурные решения

- Django 5.2 LTS monolith: один кодовый контур для admin, internal pages и public machine pages.
- Admin-first: операционная часть строится на Django Admin + Unfold, а high-value internal screens идут отдельными Django views без SPA-слоя.
- Public/private separation: публичный доступ только по `public_token`, без внутренних идентификаторов и без переиспользования приватных шаблонов.
- Domain apps: границы определены по бизнес-доменам, а не по техническим слоям, чтобы сервисные процессы, гарантия и техника развивались независимо.
- Server-rendered UI: Django templates + HTMX для быстрых интеракций, без обязательного frontend framework runtime.
- Storage abstraction: Django `STORAGES` и env-driven backend selection, чтобы локальный диск и S3-compatible storage переключались без переделки бизнес-кода.
- Growth path: DRF оставлен точечным инструментом для интеграций и future mobile/internal widgets, а не как primary interface.
- Russian-first product: `ru` по умолчанию, локальные help texts, timezone `Europe/Moscow`, self-hosted-friendly инфраструктура без обязательных внешних SaaS.

## URL стратегия

- Public: `/`, `/about/`, `/contact/`, `/m/<public_token>/`, `/m/<public_token>/request/`, `/request/success/`
- Internal: `/admin/`, `/dashboard/`, `/machines/`, `/machines/<id>/`, `/service-requests/`, `/service-calendar/`
- API: `/api/` только под целевые use cases, а не как основной transport layer

## Что подготовлено на Step 1 и Step 2

- production-oriented project skeleton
- app boundaries под будущие модели и workflow
- settings split для local/production
- dependency layer для Django, Unfold, DRF, HTMX, Celery/Redis, S3 storage
- Tailwind toolchain skeleton для public/internal custom pages

