"""
URL configuration for banking app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BankAccountViewSet, BankTransactionViewSet, ReconciliationViewSet

router = DefaultRouter()
router.register(r"accounts", BankAccountViewSet, basename="bank-account")
router.register(r"transactions", BankTransactionViewSet, basename="bank-transaction")
router.register(r"reconciliations", ReconciliationViewSet, basename="reconciliation")

urlpatterns = [
    path("", include(router.urls)),
]
