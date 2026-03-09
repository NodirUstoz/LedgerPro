"""
URL configuration for ledger app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AccountViewSet, ExchangeRateViewSet, JournalEntryViewSet, TrialBalanceView

router = DefaultRouter()
router.register(r"accounts", AccountViewSet, basename="account")
router.register(r"journal-entries", JournalEntryViewSet, basename="journal-entry")
router.register(r"trial-balance", TrialBalanceView, basename="trial-balance")
router.register(r"exchange-rates", ExchangeRateViewSet, basename="exchange-rate")

urlpatterns = [
    path("", include(router.urls)),
]
