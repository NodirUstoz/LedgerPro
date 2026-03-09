"""
Views for invoicing app.
"""

from decimal import Decimal

from django.db.models import Sum
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.ledger.services import create_journal_entry

from .models import CreditNote, Customer, Invoice, Payment
from .serializers import (
    CreditNoteSerializer,
    CustomerSerializer,
    InvoiceListSerializer,
    InvoiceSerializer,
    PaymentSerializer,
)


class CustomerViewSet(viewsets.ModelViewSet):
    """CRUD operations for customers."""

    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "email", "phone", "tax_id"]
    ordering_fields = ["name", "created_at"]

    def get_queryset(self):
        qs = Customer.objects.filter(
            company__memberships__user=self.request.user,
            company__memberships__is_active=True,
        )
        company_id = self.request.query_params.get("company")
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs.distinct()


class InvoiceViewSet(viewsets.ModelViewSet):
    """CRUD operations for invoices."""

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["invoice_number", "customer__name"]
    ordering_fields = ["issue_date", "due_date", "total_amount", "invoice_number"]

    def get_serializer_class(self):
        if self.action == "list":
            return InvoiceListSerializer
        return InvoiceSerializer

    def get_queryset(self):
        qs = Invoice.objects.filter(
            company__memberships__user=self.request.user,
            company__memberships__is_active=True,
        ).select_related("customer", "created_by")

        company_id = self.request.query_params.get("company")
        if company_id:
            qs = qs.filter(company_id=company_id)

        inv_status = self.request.query_params.get("status")
        if inv_status:
            qs = qs.filter(status=inv_status)

        customer_id = self.request.query_params.get("customer")
        if customer_id:
            qs = qs.filter(customer_id=customer_id)

        return qs.distinct()

    @action(detail=True, methods=["post"])
    def send_invoice(self, request, pk=None):
        """Mark invoice as sent and create the journal entry (AR Dr, Revenue Cr)."""
        invoice = self.get_object()

        if invoice.status != Invoice.Status.DRAFT:
            return Response(
                {"error": "Only draft invoices can be sent."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create journal entry for the invoice
        if invoice.accounts_receivable and invoice.revenue_account:
            lines = [
                {
                    "account_id": str(invoice.accounts_receivable.id),
                    "debit_amount": str(invoice.total_amount),
                    "credit_amount": "0.00",
                    "description": f"AR for Invoice {invoice.invoice_number}",
                },
                {
                    "account_id": str(invoice.revenue_account.id),
                    "debit_amount": "0.00",
                    "credit_amount": str(invoice.subtotal),
                    "description": f"Revenue for Invoice {invoice.invoice_number}",
                },
            ]

            # Add tax line if applicable
            if invoice.tax_amount > 0:
                from apps.ledger.models import Account, AccountSubType
                tax_payable = Account.objects.filter(
                    company=invoice.company,
                    sub_type=AccountSubType.TAX_PAYABLE,
                    is_active=True,
                ).first()
                if tax_payable:
                    lines.append({
                        "account_id": str(tax_payable.id),
                        "debit_amount": "0.00",
                        "credit_amount": str(invoice.tax_amount),
                        "description": f"Tax for Invoice {invoice.invoice_number}",
                    })
                else:
                    # Adjust revenue line to include tax
                    lines[1]["credit_amount"] = str(invoice.total_amount)

            try:
                journal_entry = create_journal_entry(
                    company=invoice.company,
                    entry_date=invoice.issue_date,
                    description=f"Invoice {invoice.invoice_number} - {invoice.customer.name}",
                    lines_data=lines,
                    created_by=request.user,
                    reference=invoice.invoice_number,
                    source_module="invoicing",
                    source_id=invoice.id,
                    currency=invoice.currency,
                    exchange_rate=invoice.exchange_rate,
                    auto_post=True,
                )
                invoice.journal_entry = journal_entry
            except Exception as e:
                return Response(
                    {"error": f"Failed to create journal entry: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        invoice.status = Invoice.Status.SENT
        invoice.save(update_fields=["status", "journal_entry"])

        return Response(InvoiceSerializer(invoice, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def void_invoice(self, request, pk=None):
        """Void an invoice."""
        invoice = self.get_object()

        if invoice.status in [Invoice.Status.PAID, Invoice.Status.VOIDED]:
            return Response(
                {"error": "Cannot void a paid or already voided invoice."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if invoice.journal_entry:
            from apps.ledger.services import void_journal_entry
            try:
                void_journal_entry(invoice.journal_entry, request.user)
            except Exception:
                pass

        invoice.status = Invoice.Status.VOIDED
        invoice.save(update_fields=["status"])

        return Response({"message": f"Invoice {invoice.invoice_number} voided."})

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Get invoicing summary statistics."""
        company_id = request.query_params.get("company")
        if not company_id:
            return Response(
                {"error": "company parameter required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invoices = Invoice.objects.filter(company_id=company_id)
        summary = {
            "total_invoices": invoices.count(),
            "draft": invoices.filter(status=Invoice.Status.DRAFT).count(),
            "sent": invoices.filter(status=Invoice.Status.SENT).count(),
            "paid": invoices.filter(status=Invoice.Status.PAID).count(),
            "overdue": invoices.filter(status=Invoice.Status.OVERDUE).count(),
            "total_outstanding": invoices.filter(
                status__in=[Invoice.Status.SENT, Invoice.Status.PARTIALLY_PAID, Invoice.Status.OVERDUE]
            ).aggregate(total=Sum("balance_due"))["total"] or Decimal("0.00"),
            "total_revenue": invoices.filter(
                status=Invoice.Status.PAID
            ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00"),
        }
        return Response(summary)


class PaymentViewSet(viewsets.ModelViewSet):
    """CRUD operations for payments."""

    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["payment_number", "reference"]
    ordering_fields = ["date", "amount"]

    def get_queryset(self):
        qs = Payment.objects.filter(
            company__memberships__user=self.request.user,
            company__memberships__is_active=True,
        ).select_related("invoice", "bank_account")

        company_id = self.request.query_params.get("company")
        if company_id:
            qs = qs.filter(company_id=company_id)

        invoice_id = self.request.query_params.get("invoice")
        if invoice_id:
            qs = qs.filter(invoice_id=invoice_id)

        return qs.distinct()


class CreditNoteViewSet(viewsets.ModelViewSet):
    """CRUD operations for credit notes."""

    serializer_class = CreditNoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = CreditNote.objects.filter(
            company__memberships__user=self.request.user,
            company__memberships__is_active=True,
        ).select_related("invoice")

        company_id = self.request.query_params.get("company")
        if company_id:
            qs = qs.filter(company_id=company_id)

        return qs.distinct()

    @action(detail=True, methods=["post"])
    def apply(self, request, pk=None):
        """Apply a credit note to reduce the invoice balance."""
        credit_note = self.get_object()

        if credit_note.status != CreditNote.Status.ISSUED:
            return Response(
                {"error": "Only issued credit notes can be applied."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invoice = credit_note.invoice
        invoice.amount_paid += credit_note.amount
        invoice.update_payment_status()

        credit_note.status = CreditNote.Status.APPLIED
        credit_note.save(update_fields=["status"])

        return Response({
            "message": f"Credit note {credit_note.credit_note_number} applied.",
            "invoice_balance_due": str(invoice.balance_due),
        })
