from __future__ import annotations

from datetime import timedelta

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.accounts.models import User
from apps.branches.models import Branch, Region
from apps.dealers.models import Dealer
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


class OrganizationFactory(DjangoModelFactory):
    class Meta:
        model = Organization

    name = factory.Sequence(lambda n: f"Организация {n}")
    code = factory.Sequence(lambda n: f"org-{n}")
    legal_name = factory.LazyAttribute(lambda obj: obj.name)
    inn = factory.Sequence(lambda n: f"7701000{n:04d}")
    phone = factory.Sequence(lambda n: f"+7900100{n:04d}")
    email = factory.Sequence(lambda n: f"org{n}@example.local")


class RegionFactory(DjangoModelFactory):
    class Meta:
        model = Region

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.Sequence(lambda n: f"Регион {n}")
    code = factory.Sequence(lambda n: f"region-{n}")
    ordering = factory.Sequence(lambda n: n + 1)


class BranchFactory(DjangoModelFactory):
    class Meta:
        model = Branch

    region = factory.SubFactory(RegionFactory)
    organization = factory.LazyAttribute(lambda obj: obj.region.organization)
    name = factory.Sequence(lambda n: f"Филиал {n}")
    code = factory.Sequence(lambda n: f"branch-{n}")
    phone = factory.Sequence(lambda n: f"+7900200{n:04d}")
    emergency_phone = factory.Sequence(lambda n: f"+7900210{n:04d}")
    service_phone = factory.Sequence(lambda n: f"+7900220{n:04d}")
    service_email = factory.Sequence(lambda n: f"branch{n}@example.local")


class DealerFactory(DjangoModelFactory):
    class Meta:
        model = Dealer
        skip_postgeneration_save = True

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.Sequence(lambda n: f"Дилер {n}")
    code = factory.Sequence(lambda n: f"dealer-{n}")
    legal_name = factory.LazyAttribute(lambda obj: obj.name)
    phone = factory.Sequence(lambda n: f"+7900300{n:04d}")
    emergency_phone = factory.Sequence(lambda n: f"+7900310{n:04d}")
    email = factory.Sequence(lambda n: f"dealer{n}@example.local")

    @factory.post_generation
    def branches(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.branches.set(extracted)


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.local")
    username = factory.Sequence(lambda n: f"user{n}")
    first_name = "Тест"
    last_name = factory.Sequence(lambda n: f"Пользователь{n}")
    position = "Operator"

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        self.set_password(extracted or "password123")
        self.save(update_fields=["password"])


def assign_user_scope(
    user: User,
    *,
    role: str,
    organization: Organization | None = None,
    dealer: Dealer | None = None,
    region: Region | None = None,
    branch: Branch | None = None,
) -> User:
    profile = user.profile
    profile.role = role
    profile.organization = organization
    profile.dealer = dealer
    profile.region = region
    profile.branch = branch
    profile.save()
    return user


class MachineFactory(DjangoModelFactory):
    class Meta:
        model = Machine

    branch = factory.SubFactory(BranchFactory)
    organization = factory.LazyAttribute(lambda obj: obj.branch.organization)
    region = factory.LazyAttribute(lambda obj: obj.branch.region)
    name = factory.Sequence(lambda n: f"Машина {n}")
    model_name = factory.Sequence(lambda n: f"MD-{n:03d}")
    serial_number = factory.Sequence(lambda n: f"SN-{n:05d}")
    inventory_number = factory.Sequence(lambda n: f"INV-{n:05d}")
    category = MachineCategoryChoices.EXCAVATOR
    status = MachineStatusChoices.ACTIVE
    is_active = True
    is_public = True
    commissioning_date = factory.LazyFunction(lambda: timezone.localdate() - timedelta(days=365))
    operating_hours = 1200

    @factory.lazy_attribute
    def dealer(self):
        dealer = DealerFactory(organization=self.organization)
        dealer.branches.add(self.branch)
        return dealer


class MachineTagFactory(DjangoModelFactory):
    class Meta:
        model = MachineTag

    machine = factory.SubFactory(MachineFactory)
    organization = factory.LazyAttribute(lambda obj: obj.machine.organization)
    tag_type = MachineTagTypeChoices.HYBRID
    is_active = True


class WarrantyFactory(DjangoModelFactory):
    class Meta:
        model = Warranty

    machine = factory.SubFactory(MachineFactory)
    organization = factory.LazyAttribute(lambda obj: obj.machine.organization)
    warranty_start = factory.LazyFunction(lambda: timezone.localdate() - timedelta(days=30))
    warranty_end = factory.LazyFunction(lambda: timezone.localdate() + timedelta(days=365))
    warranty_type = WarrantyTypeChoices.STANDARD
    public_summary = "Тестовая гарантия"


class ServiceRequestFactory(DjangoModelFactory):
    class Meta:
        model = ServiceRequest

    machine = factory.SubFactory(MachineFactory)
    organization = factory.LazyAttribute(lambda obj: obj.machine.organization)
    dealer = factory.LazyAttribute(lambda obj: obj.machine.dealer)
    region = factory.LazyAttribute(lambda obj: obj.machine.region)
    branch = factory.LazyAttribute(lambda obj: obj.machine.branch)
    source = ServiceRequestSourceChoices.MANUAL
    client_name = "Клиент"
    client_phone = "+79009990000"
    client_company = "ООО Клиент"
    problem_description = "Неисправность гидросистемы и перегрев узла."
    status = ServiceRequestStatusChoices.NEW
    priority = ServiceRequestPriorityChoices.NORMAL
    consent_to_processing = True


class ServiceRecordFactory(DjangoModelFactory):
    class Meta:
        model = ServiceRecord

    machine = factory.SubFactory(MachineFactory)
    organization = factory.LazyAttribute(lambda obj: obj.machine.organization)
    branch = factory.LazyAttribute(lambda obj: obj.machine.branch)
    service_date = factory.LazyFunction(lambda: timezone.localdate() - timedelta(days=7))
    work_type = ServiceWorkTypeChoices.PREVENTIVE
    description = "Выполнены тестовые сервисные работы."
    public_summary = "Плановое обслуживание завершено."
    is_public = True
    next_maintenance_date = factory.LazyFunction(
        lambda: timezone.localdate() + timedelta(days=120)
    )
