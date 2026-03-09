"""
URL configuration for expenses app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ExpenseCategoryViewSet, ExpenseViewSet, VendorViewSet

router = DefaultRouter()
router.register(r"categories", ExpenseCategoryViewSet, basename="expense-category")
router.register(r"vendors", VendorViewSet, basename="vendor")
router.register(r"expenses", ExpenseViewSet, basename="expense")

urlpatterns = [
    path("", include(router.urls)),
]
