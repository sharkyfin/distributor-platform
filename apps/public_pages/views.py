from __future__ import annotations

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import FormView, TemplateView
from django_ratelimit.decorators import ratelimit

from apps.public_pages.forms import PublicServiceRequestForm
from apps.public_pages.services import (
    build_machine_page_context,
    create_public_service_request,
    get_public_machine_tag,
)


class PublicBaseContextMixin:
    def get_public_base_context(self) -> dict:
        return {
            "product_name": "Цифровой сервисный паспорт спецтехники",
            "contact_email": getattr(
                settings,
                "PUBLIC_CONTACT_EMAIL",
                "service@atlas-machinery.ru",
            ),
            "contact_phone": getattr(settings, "PUBLIC_CONTACT_PHONE", ""),
            "operator_name": getattr(
                settings,
                "PUBLIC_OPERATOR_NAME",
                "Сервисная служба",
            ),
            "operator_address": getattr(settings, "PUBLIC_OPERATOR_ADDRESS", "Москва, Россия"),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_public_base_context())
        return context


class LandingPageView(PublicBaseContextMixin, TemplateView):
    template_name = "public_pages/landing.html"


class AboutPageView(PublicBaseContextMixin, TemplateView):
    template_name = "public_pages/about.html"


class ContactPageView(PublicBaseContextMixin, TemplateView):
    template_name = "public_pages/contact.html"


class PublicMachineContextMixin(PublicBaseContextMixin):
    machine_tag = None
    machine = None

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        self.machine_tag = get_public_machine_tag(kwargs["public_token"])
        self.machine = self.machine_tag.machine
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_machine_page_context(self.machine))
        context["machine_tag"] = self.machine_tag
        return context


class PublicMachineDetailView(PublicMachineContextMixin, TemplateView):
    template_name = "public_pages/machine_detail.html"


@method_decorator(
    ratelimit(key="ip", rate="2/m", method="POST", block=False),
    name="dispatch",
)
@method_decorator(
    ratelimit(key="ip", rate="8/h", method="POST", block=False),
    name="dispatch",
)
class PublicServiceRequestView(PublicMachineContextMixin, FormView):
    template_name = "public_pages/machine_request_form.html"
    form_class = PublicServiceRequestForm

    def post(self, request: HttpRequest, *args, **kwargs):
        if getattr(request, "limited", False):
            form = self.get_form()
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    rate_limited=True,
                ),
                status=429,
            )
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["rate_limited"] = kwargs.get("rate_limited", False)
        return context

    def form_valid(self, form: PublicServiceRequestForm):
        payload = form.build_service_request_data()
        payload["photos"] = form.cleaned_data["photos"]
        create_public_service_request(machine=self.machine, form_data=payload)
        success_url = reverse("public_pages:request_success")
        return redirect(f"{success_url}?machine={self.machine_tag.public_token}")


class PublicServiceRequestSuccessView(PublicBaseContextMixin, TemplateView):
    template_name = "public_pages/request_success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        public_token = self.request.GET.get("machine", "")
        if public_token:
            try:
                machine_tag = get_public_machine_tag(public_token)
            except Http404:
                machine_tag = None
            context["machine_tag"] = machine_tag
            context["machine"] = machine_tag.machine if machine_tag else None
        return context
