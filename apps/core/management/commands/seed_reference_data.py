from __future__ import annotations

import base64
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User, UserRoleChoices
from apps.attachments.models import (
    Attachment,
    AttachmentFileTypeChoices,
    AttachmentVisibilityChoices,
)
from apps.auditlog.models import AuditLog
from apps.branches.models import Branch, Region
from apps.dealers.models import Contact, ContactTypeChoices, ContactVisibilityChoices, Dealer
from apps.machines.models import (
    Machine,
    MachineCategoryChoices,
    MachineStatusChoices,
    MachineTag,
    MachineTagTypeChoices,
)
from apps.organizations.models import Organization
from apps.service.models import (
    ServiceRecord,
    ServiceRequest,
    ServiceRequestPriorityChoices,
    ServiceRequestSourceChoices,
    ServiceRequestStatusChoices,
    ServiceWorkTypeChoices,
)
from apps.warranties.models import Warranty, WarrantyTypeChoices

SEED_ORG_CODE = "atlas-machinery"
SEED_EMAIL_DOMAIN = "atlas-machinery.ru"
DEFAULT_PASSWORD = "ServicePass123!"
TINY_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wn6zk0AAAAASUVORK5CYII="
)

REGION_BLUEPRINTS = [
    {"code": "msk", "name": "Центральный регион", "ordering": 10},
    {"code": "url", "name": "Уральский регион", "ordering": 20},
    {"code": "sib", "name": "Сибирский регион", "ordering": 30},
]

BRANCH_BLUEPRINTS = [
    {
        "code": "msk-main",
        "name": "Москва",
        "region_code": "msk",
        "address": "Москва, 2-я Магистральная, 18",
        "phone": "+7 495 120-10-10",
        "emergency_phone": "+7 800 555-01-01",
        "service_phone": "+7 495 120-10-20",
        "service_email": "moscow.service@atlas-machinery.ru",
        "service_contact_info": (
            "Круглосуточная сервисная диспетчеризация для центрального региона."
        ),
    },
    {
        "code": "tula",
        "name": "Тула",
        "region_code": "msk",
        "address": "Тула, Новомосковское шоссе, 32",
        "phone": "+7 4872 70-10-10",
        "emergency_phone": "+7 800 555-01-02",
        "service_phone": "+7 4872 70-10-20",
        "service_email": "tula.service@atlas-machinery.ru",
        "service_contact_info": "Локальный склад расходников и выездные инженеры по ЦФО.",
    },
    {
        "code": "ekb",
        "name": "Екатеринбург",
        "region_code": "url",
        "address": "Екатеринбург, ул. Блюхера, 88",
        "phone": "+7 343 379-10-10",
        "emergency_phone": "+7 800 555-01-03",
        "service_phone": "+7 343 379-10-20",
        "service_email": "ekb.service@atlas-machinery.ru",
        "service_contact_info": "Маршрутизация выездного сервиса по Уралу и северным площадкам.",
    },
    {
        "code": "nsk",
        "name": "Новосибирск",
        "region_code": "sib",
        "address": "Новосибирск, ул. Станционная, 60/9",
        "phone": "+7 383 227-10-10",
        "emergency_phone": "+7 800 555-01-04",
        "service_phone": "+7 383 227-10-20",
        "service_email": "nsk.service@atlas-machinery.ru",
        "service_contact_info": (
            "Поддержка крупных карьеров и промышленного строительства в Сибири."
        ),
    },
    {
        "code": "kras",
        "name": "Красноярск",
        "region_code": "sib",
        "address": "Красноярск, Северное шоссе, 15",
        "phone": "+7 391 290-10-10",
        "emergency_phone": "+7 800 555-01-05",
        "service_phone": "+7 391 290-10-20",
        "service_email": "kras.service@atlas-machinery.ru",
        "service_contact_info": "Резервная сервисная площадка и поддержка северных объектов.",
    },
]

DEALER_BLUEPRINTS = [
    {
        "code": "dealer-west",
        "name": "ТехСервис Центр",
        "legal_name": "ООО ТехСервис Центр",
        "address": "Москва, 3-я Хорошевская, 12",
        "phone": "+7 495 660-10-10",
        "emergency_phone": "+7 800 200-10-10",
        "email": "west@atlas-machinery.ru",
        "website": "https://west.atlas-machinery.ru",
        "branch_codes": ["msk-main", "tula"],
    },
    {
        "code": "dealer-ural",
        "name": "Урал Индастри Сервис",
        "legal_name": "ООО Урал Индастри Сервис",
        "address": "Екатеринбург, ул. Фронтовых Бригад, 18",
        "phone": "+7 343 300-10-10",
        "emergency_phone": "+7 800 200-20-20",
        "email": "ural@atlas-machinery.ru",
        "website": "https://ural.atlas-machinery.ru",
        "branch_codes": ["ekb"],
    },
    {
        "code": "dealer-east",
        "name": "Сибирь Карьер Сервис",
        "legal_name": "ООО Сибирь Карьер Сервис",
        "address": "Новосибирск, Северный проезд, 7",
        "phone": "+7 383 320-10-10",
        "emergency_phone": "+7 800 200-30-30",
        "email": "east@atlas-machinery.ru",
        "website": "https://east.atlas-machinery.ru",
        "branch_codes": ["nsk", "kras"],
    },
]

MACHINE_NAMES = [
    "Экскаватор карьерный",
    "Погрузчик фронтальный",
    "Грейдер дорожный",
    "Бульдозер тяжелый",
    "Кран мобильный",
]
MODEL_CODES = ["DX220", "WL350", "GR215", "BZ420", "CR180", "EX330", "LD520"]
CATEGORIES = [
    MachineCategoryChoices.EXCAVATOR,
    MachineCategoryChoices.LOADER,
    MachineCategoryChoices.GRADER,
    MachineCategoryChoices.DOZER,
    MachineCategoryChoices.CRANE,
]
WORK_TYPES = [
    ServiceWorkTypeChoices.PREVENTIVE,
    ServiceWorkTypeChoices.REPAIR,
    ServiceWorkTypeChoices.DIAGNOSTIC,
    ServiceWorkTypeChoices.WARRANTY,
    ServiceWorkTypeChoices.INSPECTION,
]
REQUEST_STATUSES = [
    ServiceRequestStatusChoices.NEW,
    ServiceRequestStatusChoices.TRIAGED,
    ServiceRequestStatusChoices.SCHEDULED,
    ServiceRequestStatusChoices.IN_PROGRESS,
    ServiceRequestStatusChoices.WAITING_PARTS,
    ServiceRequestStatusChoices.COMPLETED,
]
REQUEST_PRIORITIES = [
    ServiceRequestPriorityChoices.NORMAL,
    ServiceRequestPriorityChoices.HIGH,
    ServiceRequestPriorityChoices.CRITICAL,
    ServiceRequestPriorityChoices.LOW,
]
WARRANTY_TYPES = [
    WarrantyTypeChoices.STANDARD,
    WarrantyTypeChoices.EXTENDED,
    WarrantyTypeChoices.POWERTRAIN,
    WarrantyTypeChoices.SERVICE_CONTRACT,
]


class Command(BaseCommand):
    help = "Создает базовый набор данных для сервисного паспорта."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default=DEFAULT_PASSWORD,
            help="Пароль для служебных пользователей.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Удалить существующий набор данных и создать его заново.",
        )

    def handle(self, *args, **options):
        password = options["password"]
        reset = options["reset"]

        if Organization.all_objects.filter(code=SEED_ORG_CODE).exists():
            if not reset:
                raise CommandError(
                    "Базовый набор данных уже существует. Используйте --reset для пересоздания."
                )
            self._reset_seed_data()

        with transaction.atomic():
            dataset = self._seed_reference_data(password=password)

        self.stdout.write(self.style.SUCCESS("Базовый набор данных создан."))
        self.stdout.write("")
        self.stdout.write("Сводка:")
        self.stdout.write(f"  Организация: {dataset['organization'].name}")
        self.stdout.write(f"  Регионы: {len(dataset['regions'])}")
        self.stdout.write(f"  Филиалы: {len(dataset['branches'])}")
        self.stdout.write(f"  Дилеры: {len(dataset['dealers'])}")
        self.stdout.write(f"  Машины: {len(dataset['machines'])}")
        self.stdout.write(f"  Сервисные заявки: {dataset['service_requests_count']}")
        self.stdout.write(f"  Сервисные записи: {dataset['service_records_count']}")
        self.stdout.write("")
        self.stdout.write("Учетные записи:")
        for email, role_label in dataset["credentials"]:
            self.stdout.write(f"  {email}  |  {role_label}  |  {password}")
        self.stdout.write("")
        self.stdout.write("Публичные URL примеры:")
        for machine_tag in dataset["sample_tags"]:
            self.stdout.write(f"  /m/{machine_tag.public_token}/")

    def _reset_seed_data(self) -> None:
        seed_user_emails = User.objects.filter(email__endswith=SEED_EMAIL_DOMAIN).values_list(
            "email",
            flat=True,
        )
        AuditLog.objects.filter(user__email__in=seed_user_emails).delete()
        User.objects.filter(email__endswith=SEED_EMAIL_DOMAIN).delete()

        organization = Organization.all_objects.filter(code=SEED_ORG_CODE).first()
        if organization is None:
            return

        Attachment.all_objects.filter(organization=organization).hard_delete()
        ServiceRecord.all_objects.filter(organization=organization).hard_delete()
        ServiceRequest.all_objects.filter(organization=organization).hard_delete()
        Warranty.all_objects.filter(organization=organization).hard_delete()
        MachineTag.all_objects.filter(organization=organization).hard_delete()
        Machine.all_objects.filter(organization=organization).hard_delete()
        Contact.all_objects.filter(organization=organization).hard_delete()
        Dealer.all_objects.filter(organization=organization).hard_delete()
        Branch.all_objects.filter(organization=organization).hard_delete()
        Region.all_objects.filter(organization=organization).hard_delete()
        organization.hard_delete()

    def _seed_reference_data(self, *, password: str) -> dict:
        today = timezone.localdate()
        now = timezone.now()

        organization = Organization.objects.create(
            name="ООО Атлас Машинери Рус",
            code=SEED_ORG_CODE,
            legal_name="ООО Атлас Машинери Рус",
            inn="7701234567",
            phone="+7 495 700-10-10",
            email=f"info@{SEED_EMAIL_DOMAIN}",
            website="https://atlas-machinery.ru",
            address="Москва, Ленинградский проспект, 37",
            is_active=True,
        )

        regions = {
            item["code"]: Region.objects.create(
                organization=organization,
                code=item["code"],
                name=item["name"],
                ordering=item["ordering"],
            )
            for item in REGION_BLUEPRINTS
        }

        branches = {}
        for item in BRANCH_BLUEPRINTS:
            branch = Branch.objects.create(
                organization=organization,
                region=regions[item["region_code"]],
                code=item["code"],
                name=item["name"],
                address=item["address"],
                phone=item["phone"],
                emergency_phone=item["emergency_phone"],
                service_phone=item["service_phone"],
                service_email=item["service_email"],
                service_contact_info=item["service_contact_info"],
            )
            branches[item["code"]] = branch

        dealers = {}
        for item in DEALER_BLUEPRINTS:
            dealer = Dealer.objects.create(
                organization=organization,
                code=item["code"],
                name=item["name"],
                legal_name=item["legal_name"],
                address=item["address"],
                phone=item["phone"],
                emergency_phone=item["emergency_phone"],
                email=item["email"],
                website=item["website"],
            )
            dealer.branches.set([branches[code] for code in item["branch_codes"]])
            dealers[item["code"]] = dealer

        self._create_contacts(organization=organization, branches=branches, dealers=dealers)
        users = self._create_users(
            password=password,
            organization=organization,
            dealers=dealers,
            branches=branches,
            regions=regions,
        )

        manager = users["service_manager"]
        engineer = users["service_engineer"]
        operator = users["internal_operator"]

        machine_content_type = ContentType.objects.get_for_model(Machine)
        service_record_content_type = ContentType.objects.get_for_model(ServiceRecord)

        machines: list[Machine] = []
        service_requests: list[ServiceRequest] = []
        service_records: list[ServiceRecord] = []
        sample_tags: list[MachineTag] = []

        branch_sequence = list(branches.values())
        dealer_sequence = list(dealers.values())

        for index in range(20):
            branch = branch_sequence[index % len(branch_sequence)]
            eligible_dealers = [
                dealer for dealer in dealer_sequence if branch in dealer.branches.all()
            ]
            dealer = (
                eligible_dealers[index % len(eligible_dealers)]
                if eligible_dealers
                else dealer_sequence[0]
            )

            machine = Machine.objects.create(
                organization=organization,
                branch=branch,
                region=branch.region,
                dealer=dealer,
                name=f"{MACHINE_NAMES[index % len(MACHINE_NAMES)]} {index + 1:02d}",
                model_name=f"{MODEL_CODES[index % len(MODEL_CODES)]}-{100 + index}",
                serial_number=f"SN-ATL-{index + 1:05d}",
                inventory_number=f"INV-{index + 1:04d}",
                category=CATEGORIES[index % len(CATEGORIES)],
                status=(
                    MachineStatusChoices.SERVICE
                    if index in {4, 9, 15}
                    else MachineStatusChoices.ACTIVE
                ),
                emergency_phone=branch.emergency_phone,
                is_active=True,
                is_public=index not in {17, 19},
                commissioning_date=today - timedelta(days=500 + index * 11),
                operating_hours=900 + index * 73,
                description="Машина в сервисном учете дистрибьютора.",
            )
            machine.photo.save(
                f"machine-{index + 1:02d}.png",
                ContentFile(TINY_PNG_BYTES),
                save=True,
            )
            machines.append(machine)

            tag = MachineTag.objects.create(
                organization=organization,
                machine=machine,
                tag_type=(
                    MachineTagTypeChoices.HYBRID
                    if index % 2 == 0
                    else MachineTagTypeChoices.NFC
                ),
                is_active=True,
                issued_at=today - timedelta(days=120 - index),
            )
            if len(sample_tags) < 3:
                sample_tags.append(tag)

            if index < 6:
                Attachment.objects.create(
                    organization=organization,
                    content_type=machine_content_type,
                    object_id=machine.pk,
                    title=f"Паспорт машины {index + 1:02d}",
                    file=ContentFile(
                        (
                            f"Паспорт машины {machine.serial_number}\n"
                            f"Филиал: {branch.name}\n"
                            f"Дилер: {dealer.name}\n"
                        ).encode(),
                        name=f"passport-{machine.serial_number}.txt",
                    ),
                    file_type=AttachmentFileTypeChoices.DOCUMENT,
                    visibility=AttachmentVisibilityChoices.PUBLIC,
                    original_name=f"passport-{machine.serial_number}.txt",
                    mime_type="text/plain",
                    uploaded_by=operator,
                )

            self._create_warranty(machine=machine, today=today, index=index)

            latest_request_for_machine: ServiceRequest | None = None
            request_iterations = 1 if index < 10 else (2 if index < 14 else 0)

            for request_number in range(request_iterations):
                created_at_base = now - timedelta(days=(index * 2) + request_number)
                status = REQUEST_STATUSES[(index + request_number) % len(REQUEST_STATUSES)]
                priority = REQUEST_PRIORITIES[(index + request_number) % len(REQUEST_PRIORITIES)]
                request = ServiceRequest.objects.create(
                    organization=organization,
                    machine=machine,
                    dealer=dealer,
                    region=branch.region,
                    branch=branch,
                    source=(
                        ServiceRequestSourceChoices.PUBLIC_PAGE
                        if request_number == 0 and index % 3 == 0
                        else ServiceRequestSourceChoices.MANUAL
                    ),
                    client_name=f"Клиент {index + 1:02d}",
                    client_phone=f"+7900{index + 1:03d}{request_number:01d}00",
                    client_company=f"ООО Клиент {index + 1:02d}",
                    problem_description=(
                        "Нестабильная работа гидросистемы, требуется диагностика "
                        "и проверка давления."
                    ),
                    status=status,
                    priority=priority,
                    assigned_manager=manager if status != ServiceRequestStatusChoices.NEW else None,
                    assigned_engineer=(
                        engineer
                        if status
                        in {
                            ServiceRequestStatusChoices.SCHEDULED,
                            ServiceRequestStatusChoices.IN_PROGRESS,
                            ServiceRequestStatusChoices.WAITING_PARTS,
                            ServiceRequestStatusChoices.COMPLETED,
                        }
                        else None
                    ),
                    due_at=created_at_base + timedelta(hours=18),
                    first_response_at=(
                        created_at_base + timedelta(hours=3)
                        if status != ServiceRequestStatusChoices.NEW
                        else None
                    ),
                    consent_to_processing=True,
                    internal_note="Создано при загрузке базового набора данных.",
                )
                if status == ServiceRequestStatusChoices.COMPLETED:
                    request.resolved_at = created_at_base + timedelta(days=2)
                    request.save(update_fields=["resolved_at", "updated_at"])
                service_requests.append(request)
                latest_request_for_machine = request

            record_iterations = 1 if index < 8 else (2 if index < 16 else 0)
            for record_number in range(record_iterations):
                service_date = today - timedelta(days=45 - index + record_number * 18)
                next_maintenance_date = service_date + timedelta(days=120)
                record = ServiceRecord.objects.create(
                    organization=organization,
                    machine=machine,
                    service_request=latest_request_for_machine,
                    service_date=service_date,
                    work_type=WORK_TYPES[(index + record_number) % len(WORK_TYPES)],
                    description=(
                        "Выполнены регламентные работы, диагностика ходовой части "
                        "и обновление сервисных настроек."
                    ),
                    engineer=engineer,
                    branch=branch,
                    operating_hours=(
                        machine.operating_hours + record_number * 40
                        if machine.operating_hours
                        else None
                    ),
                    mileage_km=1000 + index * 55 if index % 4 == 0 else None,
                    public_summary=(
                        "Выполнено плановое обслуживание и обновлена отметка по следующему ТО."
                        if record_number == 0 and index % 2 == 0
                        else ""
                    ),
                    is_public=record_number == 0 and index % 2 == 0,
                    private_notes="Проверить складские остатки фильтров на следующем визите.",
                    next_maintenance_date=next_maintenance_date,
                )
                service_records.append(record)

                if index < 4 and record_number == 0:
                    Attachment.objects.create(
                        organization=organization,
                        content_type=service_record_content_type,
                        object_id=record.pk,
                        title=f"Отчет сервиса {machine.serial_number}",
                        file=ContentFile(
                            (
                                f"Отчет по обслуживанию {machine.serial_number}\n"
                                f"Дата: {record.service_date:%d.%m.%Y}\n"
                                f"Филиал: {branch.name}\n"
                            ).encode(),
                            name=f"service-report-{machine.serial_number}.txt",
                        ),
                        file_type=AttachmentFileTypeChoices.DOCUMENT,
                        visibility=(
                            AttachmentVisibilityChoices.PUBLIC
                            if record.is_public
                            else AttachmentVisibilityChoices.INTERNAL
                        ),
                        original_name=f"service-report-{machine.serial_number}.txt",
                        mime_type="text/plain",
                        uploaded_by=engineer,
                    )

        AuditLog.objects.create(
            user=users["super_admin"],
            action="seed_reference_data",
            model_name="Organization",
            object_id=organization.pk,
            summary="Загружен базовый набор данных для сервисного паспорта.",
            payload={
                "organization_code": organization.code,
                "machines": len(machines),
                "service_requests": len(service_requests),
                "service_records": len(service_records),
            },
        )

        credentials = [
            (users["super_admin"].email, "Super Admin"),
            (users["distributor_admin"].email, "Distributor Admin"),
            (users["dealer_admin"].email, "Dealer Admin"),
            (users["service_manager"].email, "Service Manager"),
            (users["service_engineer"].email, "Service Engineer"),
            (users["internal_operator"].email, "Internal Operator"),
        ]

        return {
            "organization": organization,
            "regions": list(regions.values()),
            "branches": list(branches.values()),
            "dealers": list(dealers.values()),
            "machines": machines,
            "service_requests_count": len(service_requests),
            "service_records_count": len(service_records),
            "credentials": credentials,
            "sample_tags": sample_tags,
        }

    def _create_contacts(self, *, organization, branches, dealers) -> None:
        for branch in branches.values():
            Contact.objects.create(
                organization=organization,
                branch=branch,
                full_name=f"Сервисный координатор {branch.name}",
                title="Координатор сервиса",
                phone=branch.service_phone,
                email=branch.service_email,
                contact_type=ContactTypeChoices.SERVICE,
                visibility=ContactVisibilityChoices.PUBLIC,
                public_note="Основной сервисный контакт по филиалу.",
                is_primary=True,
            )
            Contact.objects.create(
                organization=organization,
                branch=branch,
                full_name=f"Диспетчер {branch.name}",
                title="Диспетчер экстренной линии",
                phone=branch.emergency_phone,
                email=branch.service_email,
                contact_type=ContactTypeChoices.EMERGENCY,
                visibility=ContactVisibilityChoices.PUBLIC,
                public_note="Экстренная линия поддержки 24/7.",
            )

        for dealer in dealers.values():
            Contact.objects.create(
                organization=organization,
                dealer=dealer,
                full_name=f"Менеджер {dealer.name}",
                title="Сервисный менеджер дилера",
                phone=dealer.phone,
                email=dealer.email,
                contact_type=ContactTypeChoices.MANAGER,
                visibility=ContactVisibilityChoices.PUBLIC,
                public_note="Координация работ и контроль сроков по дилеру.",
            )
            Contact.objects.create(
                organization=organization,
                dealer=dealer,
                full_name=f"Оператор {dealer.name}",
                title="Оператор сервисной линии",
                phone=dealer.emergency_phone,
                email=dealer.email,
                contact_type=ContactTypeChoices.OPERATOR,
                visibility=ContactVisibilityChoices.INTERNAL,
                private_note="Только для внутреннего использования.",
            )

    def _create_users(
        self,
        *,
        password,
        organization,
        dealers,
        branches,
        regions,
    ) -> dict[str, User]:
        users: dict[str, User] = {}

        users["super_admin"] = User.objects.create_superuser(
            email=f"superadmin@{SEED_EMAIL_DOMAIN}",
            password=password,
            first_name="Системный",
            last_name="Администратор",
            position="Руководитель платформы",
        )

        users["distributor_admin"] = User.objects.create_user(
            email=f"distributor.admin@{SEED_EMAIL_DOMAIN}",
            password=password,
            first_name="Дарья",
            last_name="Кузнецова",
            position="Администратор дистрибьютора",
            phone="+79001110001",
        )
        self._update_profile(
            users["distributor_admin"],
            role=UserRoleChoices.DISTRIBUTOR_ADMIN,
            organization=organization,
        )

        users["dealer_admin"] = User.objects.create_user(
            email=f"dealer.admin@{SEED_EMAIL_DOMAIN}",
            password=password,
            first_name="Илья",
            last_name="Громов",
            position="Администратор дилера",
            phone="+79001110002",
        )
        self._update_profile(
            users["dealer_admin"],
            role=UserRoleChoices.DEALER_ADMIN,
            dealer=dealers["dealer-west"],
        )

        users["service_manager"] = User.objects.create_user(
            email=f"service.manager@{SEED_EMAIL_DOMAIN}",
            password=password,
            first_name="Анна",
            last_name="Егорова",
            position="Руководитель сервиса",
            phone="+79001110003",
        )
        self._update_profile(
            users["service_manager"],
            role=UserRoleChoices.SERVICE_MANAGER,
            organization=organization,
            region=regions["msk"],
            branch=branches["msk-main"],
        )

        users["service_engineer"] = User.objects.create_user(
            email=f"service.engineer@{SEED_EMAIL_DOMAIN}",
            password=password,
            first_name="Павел",
            last_name="Морозов",
            position="Сервисный инженер",
            phone="+79001110004",
        )
        self._update_profile(
            users["service_engineer"],
            role=UserRoleChoices.SERVICE_ENGINEER,
            organization=organization,
            branch=branches["ekb"],
            region=regions["url"],
        )

        users["internal_operator"] = User.objects.create_user(
            email=f"operator@{SEED_EMAIL_DOMAIN}",
            password=password,
            first_name="Ольга",
            last_name="Смирнова",
            position="Сервисный оператор",
            phone="+79001110005",
        )
        self._update_profile(
            users["internal_operator"],
            role=UserRoleChoices.INTERNAL_OPERATOR,
            organization=organization,
        )

        return users

    def _update_profile(
        self,
        user: User,
        *,
        role: str,
        organization: Organization | None = None,
        dealer: Dealer | None = None,
        region: Region | None = None,
        branch: Branch | None = None,
    ) -> None:
        profile = user.profile
        profile.role = role
        profile.organization = organization
        profile.dealer = dealer
        profile.region = region
        profile.branch = branch
        profile.notes = "Создано при загрузке базового набора данных."
        profile.save()

    def _create_warranty(self, *, machine: Machine, today, index: int) -> Warranty:
        status_window = index % 4
        if status_window == 0:
            start, end = today - timedelta(days=120), today + timedelta(days=240)
        elif status_window == 1:
            start, end = today - timedelta(days=300), today + timedelta(days=18)
        elif status_window == 2:
            start, end = today - timedelta(days=500), today - timedelta(days=20)
        else:
            start, end = today + timedelta(days=12), today + timedelta(days=320)

        return Warranty.objects.create(
            organization=machine.organization,
            machine=machine,
            warranty_start=start,
            warranty_end=end,
            warranty_type=WARRANTY_TYPES[index % len(WARRANTY_TYPES)],
            public_summary="Стандартное покрытие по силовой линии и выездному сервису.",
            notes="Покрытие поставки и выездного сервиса.",
        )
