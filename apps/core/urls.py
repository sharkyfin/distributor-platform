from __future__ import annotations

from django.urls import path

from apps.core.views import (
    DashboardView,
    MachineDetailView,
    MachineListView,
    ServiceCalendarView,
    ServiceRequestListView,
)

app_name = "core"

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("machines/", MachineListView.as_view(), name="machine_list"),
    path("machines/<int:pk>/", MachineDetailView.as_view(), name="machine_detail"),
    path("service-requests/", ServiceRequestListView.as_view(), name="service_requests"),
    path("service-calendar/", ServiceCalendarView.as_view(), name="service_calendar"),
]
