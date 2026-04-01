from __future__ import annotations

from django.urls import path

from apps.public_pages.views import (
    AboutPageView,
    ContactPageView,
    LandingPageView,
    PublicMachineDetailView,
    PublicServiceRequestSuccessView,
    PublicServiceRequestView,
)

app_name = "public_pages"

urlpatterns = [
    path("", LandingPageView.as_view(), name="landing"),
    path("about/", AboutPageView.as_view(), name="about"),
    path("contact/", ContactPageView.as_view(), name="contact"),
    path("m/<str:public_token>/", PublicMachineDetailView.as_view(), name="machine_detail"),
    path(
        "m/<str:public_token>/request/",
        PublicServiceRequestView.as_view(),
        name="machine_request",
    ),
    path("request/success/", PublicServiceRequestSuccessView.as_view(), name="request_success"),
]
