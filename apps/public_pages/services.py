from __future__ import annotations

from pathlib import Path

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404

from apps.attachments.models import (
    Attachment,
    AttachmentFileTypeChoices,
    AttachmentVisibilityChoices,
)
from apps.dealers.models import Contact, ContactTypeChoices, ContactVisibilityChoices
from apps.machines.models import Machine, MachineTag
from apps.service.models import (
    ServiceRequest,
    ServiceRequestPriorityChoices,
    ServiceRequestSourceChoices,
)


def get_public_machine_tag(public_token: str) -> MachineTag:
    return get_object_or_404(
        MachineTag.objects.select_related(
            "machine",
            "machine__organization",
            "machine__region",
            "machine__branch",
            "machine__dealer",
        ),
        public_token=public_token,
        is_active=True,
        machine__is_public=True,
        machine__is_active=True,
    )


def get_machine_public_warranty(machine: Machine):
    warranty = machine.current_warranty
    if warranty:
        return warranty
    return machine.warranties.order_by("-warranty_end").first()


def get_machine_public_contacts(machine: Machine):
    scope_filter = Q(branch=machine.branch)

    if machine.dealer_id:
        scope_filter |= Q(dealer=machine.dealer)

    scope_filter |= Q(branch__isnull=True, dealer__isnull=True)

    return (
        Contact.objects.filter(
            organization=machine.organization,
            visibility=ContactVisibilityChoices.PUBLIC,
        )
        .filter(scope_filter)
        .select_related("dealer", "branch")
        .order_by("-is_primary", "contact_type", "full_name")
    )


def get_machine_public_documents(machine: Machine):
    return (
        Attachment.objects.filter(
            Q(machine=machine)
            | Q(service_record__machine=machine, service_record__is_public=True),
            visibility=AttachmentVisibilityChoices.PUBLIC,
        )
        .distinct()
        .order_by("-created_at")
    )


def get_machine_public_history(machine: Machine):
    return (
        machine.service_records.filter(is_public=True)
        .select_related("engineer", "branch")
        .order_by("-service_date", "-created_at")
    )


def get_machine_emergency_phone(machine: Machine):
    return (
        machine.emergency_phone
        or machine.branch.emergency_phone
        or (machine.dealer.emergency_phone if machine.dealer else None)
        or machine.branch.service_phone
        or (machine.dealer.phone if machine.dealer else None)
    )


def classify_public_contact(contact: Contact) -> str:
    if contact.contact_type == ContactTypeChoices.EMERGENCY:
        return "Экстренная линия"
    if contact.contact_type == ContactTypeChoices.MANAGER:
        return "Менеджер"
    if contact.contact_type == ContactTypeChoices.OPERATOR:
        return "Оператор"
    if contact.contact_type == ContactTypeChoices.SALES:
        return "Коммерческий контакт"
    return "Сервисный контакт"


def build_machine_page_context(machine: Machine) -> dict:
    public_contacts = list(get_machine_public_contacts(machine))
    public_history = list(get_machine_public_history(machine)[:5])
    public_documents = list(get_machine_public_documents(machine)[:10])
    warranty = get_machine_public_warranty(machine)

    service_contacts = [
        {
            "name": contact.full_name,
            "title": contact.title or classify_public_contact(contact),
            "phone": contact.phone,
            "email": contact.email,
            "note": contact.public_note,
        }
        for contact in public_contacts
    ]

    dealer_name = machine.dealer.name if machine.dealer else machine.organization.name

    return {
        "machine": machine,
        "dealer_name": dealer_name,
        "warranty": warranty,
        "service_contacts": service_contacts,
        "public_documents": public_documents,
        "public_history": public_history,
        "emergency_phone": get_machine_emergency_phone(machine),
        "service_phone": (
            machine.branch.service_phone
            or (machine.dealer.phone if machine.dealer else None)
        ),
        "service_email": (
            machine.branch.service_email
            or (machine.dealer.email if machine.dealer else "")
        ),
        "service_contact_info": machine.branch.service_contact_info,
    }


def _attachment_title(filename: str, index: int) -> str:
    stem = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
    return stem[:90] if stem else f"Фото обращения {index}"


@transaction.atomic
def create_public_service_request(
    *,
    machine: Machine,
    form_data: dict,
) -> ServiceRequest:
    service_request = ServiceRequest.objects.create(
        organization=machine.organization,
        machine=machine,
        dealer=machine.dealer,
        region=machine.region,
        branch=machine.branch,
        source=ServiceRequestSourceChoices.PUBLIC_PAGE,
        status="new",
        priority=ServiceRequestPriorityChoices.NORMAL,
        client_name=form_data["client_name"],
        client_phone=form_data["client_phone"],
        client_company=form_data["client_company"],
        problem_description=form_data["problem_description"],
        consent_to_processing=form_data["consent_to_processing"],
    )

    content_type = ContentType.objects.get_for_model(ServiceRequest)
    for index, uploaded_file in enumerate(form_data.get("photos", []), start=1):
        Attachment.objects.create(
            organization=machine.organization,
            content_type=content_type,
            object_id=service_request.pk,
            title=_attachment_title(uploaded_file.name, index),
            file=uploaded_file,
            file_type=AttachmentFileTypeChoices.IMAGE,
            visibility=AttachmentVisibilityChoices.INTERNAL,
            original_name=uploaded_file.name,
            mime_type=getattr(uploaded_file, "content_type", ""),
            size=uploaded_file.size,
        )

    return service_request
