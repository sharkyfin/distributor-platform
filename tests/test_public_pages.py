from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.attachments.models import Attachment, AttachmentVisibilityChoices
from apps.service.models import (
    ServiceRequest,
    ServiceRequestSourceChoices,
    ServiceRequestStatusChoices,
)
from tests.factories import MachineFactory, MachineTagFactory


def test_public_service_request_creates_internal_ticket(client, db):
    machine = MachineFactory()
    tag = MachineTagFactory(machine=machine, organization=machine.organization)

    response = client.post(
        reverse("public_pages:machine_request", args=[tag.public_token]),
        data={
            "name": "Иван Петров",
            "phone": "+79001234567",
            "company": "ООО Клиент",
            "problem_description": (
                "Техника теряет давление в гидросистеме и останавливается под нагрузкой."
            ),
            "consent": "on",
            "photos": [
                SimpleUploadedFile(
                    "issue.png",
                    b"png",
                    content_type="image/png",
                )
            ],
        },
    )

    assert response.status_code == 302
    assert response.url.startswith(reverse("public_pages:request_success"))

    service_request = ServiceRequest.objects.get()
    assert service_request.machine == machine
    assert service_request.source == ServiceRequestSourceChoices.PUBLIC_PAGE
    assert service_request.status == ServiceRequestStatusChoices.NEW
    assert service_request.branch == machine.branch
    assert service_request.region == machine.region

    attachment = Attachment.objects.get()
    assert attachment.content_object == service_request
    assert attachment.visibility == AttachmentVisibilityChoices.INTERNAL
