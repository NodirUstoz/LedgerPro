"""
URL configuration for the reports app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import FinancialStatementViewSet, ReportScheduleViewSet, SavedReportViewSet

router = DefaultRouter()
router.register(r"statements", FinancialStatementViewSet, basename="financial-statement")
router.register(r"saved", SavedReportViewSet, basename="saved-report")
router.register(r"schedules", ReportScheduleViewSet, basename="report-schedule")

urlpatterns = [
    path("", include(router.urls)),
]
