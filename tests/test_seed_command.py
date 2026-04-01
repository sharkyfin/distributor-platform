from __future__ import annotations

from io import StringIO

from django.core.management import call_command

from apps.accounts.models import User
from apps.branches.models import Branch, Region
from apps.machines.models import Machine, MachineTag
from apps.organizations.models import Organization
from apps.service.models import ServiceRecord, ServiceRequest
from apps.warranties.models import Warranty


def test_seed_reference_data_command_creates_expected_dataset(db):
    out = StringIO()

    call_command("seed_reference_data", password="ServicePass123!", stdout=out)

    assert Organization.objects.filter(code="atlas-machinery").count() == 1
    assert Region.objects.count() == 3
    assert Branch.objects.count() == 5
    assert Machine.objects.count() == 20
    assert MachineTag.objects.count() == 20
    assert MachineTag.objects.filter(is_active=True).count() == 20
    assert Warranty.objects.count() == 20
    assert ServiceRequest.objects.count() == 18
    assert ServiceRecord.objects.count() == 24
    assert User.objects.filter(email__endswith="atlas-machinery.ru").count() == 6

    output = out.getvalue()
    assert "Базовый набор данных создан." in output
    assert "/m/" in output
