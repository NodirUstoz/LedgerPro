"""
Views for expenses app.
"""

from decimal import Decimal

from django.db.models import Sum
from rest_framework import filters, parsers, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.ledger.services import create_journal_entry

from .models import Expense, ExpenseCategory, Receipt, Vendor
from .serializers import (
    ExpenseCategorySerializer,
    ExpenseListSerializer,
    ExpenseSerializer,
    ReceiptSerializer,
    VendorSerializer,
)


class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    """CRUD operations for expense categories."""

    serializer_class = ExpenseCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ExpenseCategory.objects.filter(
            company__memberships__user=self.request.user,
            company__memberships__is_active=True,
        )
        company_id = self.request.query_params.get("company")
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs.distinct()


class VendorViewSet(viewsets.ModelViewSet):
    """CRUD operations for vendors."""

    serializer_class = VendorSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "email", "tax_id"]

    def get_queryset(self):
        qs = Vendor.objects.filter(
            company__memberships__user=self.request.user,
            company__memberships__is_active=True,
        )
        company_id = self.request.query_params.get("company")
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs.distinct()


class ExpenseViewSet(viewsets.ModelViewSet):
    """CRUD operations for expenses."""

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["expense_number", "description", "vendor__name"]
    ordering_fields = ["date", "total_amount", "created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return ExpenseListSerializer
        return ExpenseSerializer

    def get_queryset(self):
        qs = Expense.objects.filter(
            company__memberships__user=self.request.user,
            company__memberships__is_active=True,
        ).select_related("vendor", "category", "created_by")

        company_id = self.request.query_params.get("company")
        if company_id:
            qs = qs.filter(company_id=company_id)

        exp_status = self.request.query_params.get("status")
        if exp_status:
            qs = qs.filter(status=exp_status)

        category_id = self.request.query_params.get("category")
        if category_id:
            qs = qs.filter(category_id=category_id)

        vendor_id = self.request.query_params.get("vendor")
        if vendor_id:
            qs = qs.filter(vendor_id=vendor_id)

        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)

        return qs.distinct()

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a pending expense."""
        expense = self.get_object()
        if expense.status not in [Expense.Status.DRAFT, Expense.Status.PENDING]:
            return Response(
                {"error": "Only draft or pending expenses can be approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        expense.status = Expense.Status.APPROVED
        expense.approved_by = request.user
        expense.save(update_fields=["status", "approved_by"])

        return Response(ExpenseSerializer(expense, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject a pending expense."""
        expense = self.get_object()
        if expense.status not in [Expense.Status.DRAFT, Expense.Status.PENDING]:
            return Response(
                {"error": "Only draft or pending expenses can be rejected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        expense.status = Expense.Status.REJECTED
        expense.save(update_fields=["status"])

        return Response({"message": f"Expense {expense.expense_number} rejected."})

    @action(detail=True, methods=["post"])
    def record_payment(self, request, pk=None):
        """
        Record payment of an approved expense and create the journal entry
        (Expense Dr, Payment Account Cr).
        """
        expense = self.get_object()
        if expense.status != Expense.Status.APPROVED:
            return Response(
                {"error": "Only approved expenses can be paid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if expense.expense_account and expense.payment_account:
            lines = [
                {
                    "account_id": str(expense.expense_account.id),
                    "debit_amount": str(expense.total_amount),
                    "credit_amount": "0.00",
                    "description": f"Expense: {expense.description[:100]}",
                },
                {
                    "account_id": str(expense.payment_account.id),
                    "debit_amount": "0.00",
                    "credit_amount": str(expense.total_amount),
                    "description": f"Payment for {expense.expense_number}",
                },
            ]

            try:
                journal_entry = create_journal_entry(
                    company=expense.company,
                    entry_date=expense.date,
                    description=f"Expense {expense.expense_number} - {expense.description[:80]}",
                    lines_data=lines,
                    created_by=request.user,
                    reference=expense.reference or expense.expense_number,
                    source_module="expenses",
                    source_id=expense.id,
                    currency=expense.currency,
                    exchange_rate=expense.exchange_rate,
                    auto_post=True,
                )
                expense.journal_entry = journal_entry
            except Exception as e:
                return Response(
                    {"error": f"Failed to create journal entry: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        expense.status = Expense.Status.PAID
        expense.save(update_fields=["status", "journal_entry"])

        return Response(ExpenseSerializer(expense, context={"request": request}).data)

    @action(
        detail=True,
        methods=["post"],
        parser_classes=[parsers.MultiPartParser, parsers.FormParser],
    )
    def upload_receipt(self, request, pk=None):
        """Upload a receipt file for an expense."""
        expense = self.get_object()
        file = request.FILES.get("file")

        if not file:
            return Response(
                {"error": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        receipt = Receipt.objects.create(
            expense=expense,
            file=file,
            filename=file.name,
            file_size=file.size,
            mime_type=file.content_type or "application/octet-stream",
            uploaded_by=request.user,
        )

        return Response(
            ReceiptSerializer(receipt).data, status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Get expense summary by category for a date range."""
        company_id = request.query_params.get("company")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        if not company_id:
            return Response(
                {"error": "company parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        expenses = Expense.objects.filter(
            company_id=company_id,
            status__in=[Expense.Status.APPROVED, Expense.Status.PAID],
        )

        if start_date:
            expenses = expenses.filter(date__gte=start_date)
        if end_date:
            expenses = expenses.filter(date__lte=end_date)

        by_category = expenses.values(
            "category__name"
        ).annotate(
            total=Sum("total_amount")
        ).order_by("-total")

        total = expenses.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")

        return Response({
            "total_expenses": total,
            "by_category": list(by_category),
            "count": expenses.count(),
        })
