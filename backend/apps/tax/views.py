"""
Views for the tax app.
"""

from datetime import date
from decimal import Decimal

from django.db.models import Sum
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.ledger.models import JournalEntry, JournalLine
from apps.ledger.services import create_journal_entry

from .models import TaxExemption, TaxFiling, TaxRate
from .serializers import (
    TaxCalculationRequestSerializer,
    TaxExemptionSerializer,
    TaxFilingListSerializer,
    TaxFilingSerializer,
    TaxRateListSerializer,
    TaxRateSerializer,
)


class TaxRateViewSet(viewsets.ModelViewSet):
    """CRUD operations for tax rates."""

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "code"]
    ordering_fields = ["name", "rate", "tax_type"]
    ordering = ["name"]

    def get_serializer_class(self):
        if self.action == "list":
            return TaxRateListSerializer
        return TaxRateSerializer

    def get_queryset(self):
        qs = TaxRate.objects.filter(
            company__memberships__user=self.request.user,
            company__memberships__is_active=True,
        ).select_related("tax_account")

        company_id = self.request.query_params.get("company")
        if company_id:
            qs = qs.filter(company_id=company_id)

        tax_type = self.request.query_params.get("tax_type")
        if tax_type:
            qs = qs.filter(tax_type=tax_type)

        applies_to = self.request.query_params.get("applies_to")
        if applies_to:
            qs = qs.filter(applies_to__in=[applies_to, "both"])

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")

        return qs.distinct()

    @action(detail=False, methods=["post"])
    def calculate(self, request):
        """Calculate tax for a given amount and tax rate."""
        serializer = TaxCalculationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            tax_rate = TaxRate.objects.get(
                id=serializer.validated_data["tax_rate_id"],
                is_active=True,
            )
        except TaxRate.DoesNotExist:
            return Response(
                {"error": "Tax rate not found or inactive."},
                status=status.HTTP_404_NOT_FOUND,
            )

        amount = serializer.validated_data["amount"]
        tax_amount = tax_rate.calculate_tax(amount)

        if tax_rate.is_inclusive:
            net_amount = amount - tax_amount
            gross_amount = amount
        else:
            net_amount = amount
            gross_amount = amount + tax_amount

        return Response({
            "tax_rate_name": tax_rate.name,
            "tax_rate_percent": str(tax_rate.rate),
            "net_amount": str(net_amount.quantize(Decimal("0.01"))),
            "tax_amount": str(tax_amount.quantize(Decimal("0.01"))),
            "gross_amount": str(gross_amount.quantize(Decimal("0.01"))),
        })


class TaxFilingViewSet(viewsets.ModelViewSet):
    """CRUD operations for tax filings."""

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["period_end", "filing_deadline", "total_due"]
    ordering = ["-period_end"]

    def get_serializer_class(self):
        if self.action == "list":
            return TaxFilingListSerializer
        return TaxFilingSerializer

    def get_queryset(self):
        qs = TaxFiling.objects.filter(
            company__memberships__user=self.request.user,
            company__memberships__is_active=True,
        ).select_related("prepared_by")

        company_id = self.request.query_params.get("company")
        if company_id:
            qs = qs.filter(company_id=company_id)

        filing_status = self.request.query_params.get("status")
        if filing_status:
            qs = qs.filter(status=filing_status)

        tax_type = self.request.query_params.get("tax_type")
        if tax_type:
            qs = qs.filter(tax_type=tax_type)

        return qs.distinct()

    def perform_create(self, serializer):
        serializer.save(prepared_by=self.request.user)

    @action(detail=True, methods=["post"])
    def calculate(self, request, pk=None):
        """
        Calculate tax liability for the filing period by aggregating
        tax amounts from posted journal entries.
        """
        filing = self.get_object()

        if filing.status == TaxFiling.FilingStatus.FILED:
            return Response(
                {"error": "Cannot recalculate a filed tax return."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Aggregate tax collected from sales (credit-side tax lines)
        sales_tax_lines = JournalLine.objects.filter(
            journal_entry__company=filing.company,
            journal_entry__status=JournalEntry.Status.POSTED,
            journal_entry__date__gte=filing.period_start,
            journal_entry__date__lte=filing.period_end,
            tax_rate__tax_type=filing.tax_type,
            credit_amount__gt=Decimal("0.00"),
        )
        collected = sales_tax_lines.aggregate(
            total=Sum("base_credit_amount")
        )["total"] or Decimal("0.00")

        # Aggregate input tax from purchases (debit-side tax lines)
        purchase_tax_lines = JournalLine.objects.filter(
            journal_entry__company=filing.company,
            journal_entry__status=JournalEntry.Status.POSTED,
            journal_entry__date__gte=filing.period_start,
            journal_entry__date__lte=filing.period_end,
            tax_rate__tax_type=filing.tax_type,
            debit_amount__gt=Decimal("0.00"),
        )
        input_tax = purchase_tax_lines.aggregate(
            total=Sum("base_debit_amount")
        )["total"] or Decimal("0.00")

        filing.total_tax_collected = collected
        filing.total_input_tax = input_tax
        filing.calculate_liability()

        return Response(TaxFilingSerializer(filing).data)

    @action(detail=True, methods=["post"])
    def file(self, request, pk=None):
        """Mark the tax filing as filed."""
        filing = self.get_object()

        if filing.status not in [
            TaxFiling.FilingStatus.CALCULATED,
            TaxFiling.FilingStatus.DRAFT,
        ]:
            return Response(
                {"error": "Only draft or calculated filings can be filed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        confirmation = request.data.get("confirmation_number", "")
        filing.status = TaxFiling.FilingStatus.FILED
        filing.filed_date = date.today()
        filing.confirmation_number = confirmation
        filing.save(update_fields=["status", "filed_date", "confirmation_number"])

        return Response(TaxFilingSerializer(filing).data)

    @action(detail=True, methods=["post"])
    def record_payment(self, request, pk=None):
        """Record a tax payment and create the associated journal entry."""
        filing = self.get_object()

        if filing.status != TaxFiling.FilingStatus.FILED:
            return Response(
                {"error": "Tax payment can only be recorded for filed returns."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment_account_id = request.data.get("payment_account_id")
        if not payment_account_id:
            return Response(
                {"error": "payment_account_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tax_rates = TaxRate.objects.filter(
            company=filing.company,
            tax_type=filing.tax_type,
            tax_account__isnull=False,
            is_active=True,
        )
        tax_account = tax_rates.first()
        if not tax_account or not tax_account.tax_account:
            return Response(
                {"error": "No tax liability account configured for this tax type."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lines = [
            {
                "account_id": str(tax_account.tax_account.id),
                "debit_amount": str(filing.total_due),
                "credit_amount": "0.00",
                "description": f"Tax payment for {filing.name}",
            },
            {
                "account_id": payment_account_id,
                "debit_amount": "0.00",
                "credit_amount": str(filing.total_due),
                "description": f"Payment - {filing.name}",
            },
        ]

        try:
            journal_entry = create_journal_entry(
                company=filing.company,
                entry_date=date.today(),
                description=f"Tax payment: {filing.name}",
                lines_data=lines,
                created_by=request.user,
                reference=filing.confirmation_number or f"TAX-{filing.id}",
                source_module="tax",
                source_id=filing.id,
                auto_post=True,
            )
            filing.journal_entry = journal_entry
            filing.save(update_fields=["journal_entry"])
        except Exception as e:
            return Response(
                {"error": f"Failed to create journal entry: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(TaxFilingSerializer(filing).data)


class TaxExemptionViewSet(viewsets.ModelViewSet):
    """CRUD operations for tax exemptions."""

    serializer_class = TaxExemptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["certificate_number", "customer__name", "issuing_authority"]

    def get_queryset(self):
        qs = TaxExemption.objects.filter(
            company__memberships__user=self.request.user,
            company__memberships__is_active=True,
        ).select_related("customer")

        company_id = self.request.query_params.get("company")
        if company_id:
            qs = qs.filter(company_id=company_id)

        customer_id = self.request.query_params.get("customer")
        if customer_id:
            qs = qs.filter(customer_id=customer_id)

        active_only = self.request.query_params.get("active_only")
        if active_only and active_only.lower() == "true":
            from datetime import date as date_cls
            today = date_cls.today()
            qs = qs.filter(
                is_active=True,
                effective_from__lte=today,
            ).exclude(effective_to__lt=today)

        return qs.distinct()
