from __future__ import annotations

from django.urls import reverse

from apps.accounts.models import UserRoleChoices
from tests.factories import (
    BranchFactory,
    DealerFactory,
    MachineFactory,
    OrganizationFactory,
    RegionFactory,
    UserFactory,
    assign_user_scope,
)


def test_dashboard_requires_authentication(client):
    response = client.get(reverse("core:dashboard"))

    assert response.status_code == 302
    assert reverse("admin:login") in response.url


def test_dealer_admin_sees_only_scoped_machines(client, db):
    organization_a = OrganizationFactory()
    region_a = RegionFactory(organization=organization_a)
    branch_a = BranchFactory(organization=organization_a, region=region_a)
    dealer_a = DealerFactory(organization=organization_a, branches=[branch_a])

    organization_b = OrganizationFactory()
    region_b = RegionFactory(organization=organization_b)
    branch_b = BranchFactory(organization=organization_b, region=region_b)
    dealer_b = DealerFactory(organization=organization_b, branches=[branch_b])

    visible_machine = MachineFactory(
        organization=organization_a,
        region=region_a,
        branch=branch_a,
        dealer=dealer_a,
        name="Видимая машина",
    )
    MachineFactory(
        organization=organization_b,
        region=region_b,
        branch=branch_b,
        dealer=dealer_b,
        name="Чужая машина",
    )

    user = UserFactory(password="password123")
    assign_user_scope(user, role=UserRoleChoices.DEALER_ADMIN, dealer=dealer_a)
    client.force_login(user)

    response = client.get(reverse("core:machine_list"))

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert visible_machine.name in content
    assert "Чужая машина" not in content

