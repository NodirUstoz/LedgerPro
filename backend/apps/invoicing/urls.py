"""
URL configuration for invoicing app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CreditNoteViewSet, CustomerViewSet, InvoiceViewSet, PaymentViewSet

router = DefaultRouter()
router.register(r"customers", CustomerViewSet, basename="customer")
router.register(r"invoices", InvoiceViewSet, basename="invoice")
router.register(r"payments", PaymentViewSet, basename="payment")
router.register(r"credit-notes", CreditNoteViewSet, basename="credit-note")

urlpatterns = [
    path("", include(router.urls)),
]
