"""
URL configuration for the tax app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TaxExemptionViewSet, TaxFilingViewSet, TaxRateViewSet

router = DefaultRouter()
router.register(r"rates", TaxRateViewSet, basename="tax-rate")
router.register(r"filings", TaxFilingViewSet, basename="tax-filing")
router.register(r"exemptions", TaxExemptionViewSet, basename="tax-exemption")

urlpatterns = [
    path("", include(router.urls)),
]
