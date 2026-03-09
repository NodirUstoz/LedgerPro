"""
Views for banking app.
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import BankAccount, BankTransaction, Reconciliation
from .serializers import (
    BankAccountSerializer,
    BankTransactionListSerializer,
    BankTransactionSerializer,
    ReconciliationSerializer,
)


class BankAccountViewSet(viewsets.ModelViewSet):
    """CRUD operations for bank accounts."""

    serializer_class = BankAccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "bank_name"]

    def get_queryset(self):
        qs = BankAccount.objects.filter(
            company__memberships__user=self.request.user,
            company__memberships__is_active=True,
        ).select_related("ledger_account")

        company_id = self.request.query_params.get("company")
        if company_id:
            qs = qs.filter(company_id=company_id)

        return qs.distinct()

    @action(detail=True, methods=["get"])
    def transactions(self, request, pk=None):
        """List all transactions for a bank account."""
        bank_account = self.get_object()
        transactions = bank_account.transactions.all()

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        tx_status = request.query_params.get("status")

        if start_date:
            transactions = transactions.filter(date__gte=start_date)
        if end_date:
            transactions = transactions.filter(date__lte=end_date)
        if tx_status:
            transactions = transactions.filter(status=tx_status)

        from utils.pagination import StandardResultsSetPagination
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(transactions, request)
        serializer = BankTransactionListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=True, methods=["post"])
    def import_transactions(self, request, pk=None):
        """Import bank transactions from uploaded data (CSV format expected)."""
        bank_account = self.get_object()
        transactions_data = request.data.get("transactions", [])

        if not transactions_data:
            return Response(
                {"error": "No transactions provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        import_batch = f"IMP-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        created = []

        for tx_data in transactions_data:
            # Skip duplicates by external_id
            external_id = tx_data.get("external_id", "")
            if external_id and BankTransaction.objects.filter(
                bank_account=bank_account, external_id=external_id
            ).exists():
                continue

            tx = BankTransaction.objects.create(
                bank_account=bank_account,
                date=tx_data["date"],
                description=tx_data["description"],
                reference=tx_data.get("reference", ""),
                transaction_type=tx_data.get("transaction_type", "other"),
                amount=Decimal(str(tx_data["amount"])),
                payee=tx_data.get("payee", ""),
                external_id=external_id,
                import_batch=import_batch,
                status=BankTransaction.Status.PENDING,
            )
            created.append(tx.id)

        return Response({
            "message": f"Imported {len(created)} transactions.",
            "import_batch": import_batch,
            "count": len(created),
        }, status=status.HTTP_201_CREATED)


class BankTransactionViewSet(viewsets.ModelViewSet):
    """CRUD operations for bank transactions."""

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["description", "payee", "reference"]
    ordering_fields = ["date", "amount"]

    def get_serializer_class(self):
        if self.action == "list":
            return BankTransactionListSerializer
        return BankTransactionSerializer

    def get_queryset(self):
        qs = BankTransaction.objects.filter(
            bank_account__company__memberships__user=self.request.user,
            bank_account__company__memberships__is_active=True,
        ).select_related("bank_account", "category")

        bank_account_id = self.request.query_params.get("bank_account")
        if bank_account_id:
            qs = qs.filter(bank_account_id=bank_account_id)

        tx_status = self.request.query_params.get("status")
        if tx_status:
            qs = qs.filter(status=tx_status)

        return qs.distinct()

    @action(detail=True, methods=["post"])
    def match(self, request, pk=None):
        """Match a bank transaction to a journal entry line."""
        tx = self.get_object()
        journal_line_id = request.data.get("journal_line_id")

        if not journal_line_id:
            return Response(
                {"error": "journal_line_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.ledger.models import JournalLine
        try:
            journal_line = JournalLine.objects.get(id=journal_line_id)
        except JournalLine.DoesNotExist:
            return Response(
                {"error": "Journal line not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        tx.matched_journal_line = journal_line
        tx.journal_entry = journal_line.journal_entry
        tx.status = BankTransaction.Status.CLEARED
        tx.save(update_fields=["matched_journal_line", "journal_entry", "status"])

        journal_line.reconciled = True
        journal_line.save(update_fields=["reconciled"])

        return Response(BankTransactionSerializer(tx).data)

    @action(detail=True, methods=["post"])
    def unmatch(self, request, pk=None):
        """Unmatch a bank transaction from its journal entry."""
        tx = self.get_object()

        if tx.matched_journal_line:
            tx.matched_journal_line.reconciled = False
            tx.matched_journal_line.save(update_fields=["reconciled"])

        tx.matched_journal_line = None
        tx.journal_entry = None
        tx.status = BankTransaction.Status.PENDING
        tx.save(update_fields=["matched_journal_line", "journal_entry", "status"])

        return Response(BankTransactionSerializer(tx).data)


class ReconciliationViewSet(viewsets.ModelViewSet):
    """CRUD operations for bank reconciliations."""

    serializer_class = ReconciliationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Reconciliation.objects.filter(
            bank_account__company__memberships__user=self.request.user,
            bank_account__company__memberships__is_active=True,
        ).select_related("bank_account")

        bank_account_id = self.request.query_params.get("bank_account")
        if bank_account_id:
            qs = qs.filter(bank_account_id=bank_account_id)

        return qs.distinct()

    @action(detail=True, methods=["post"])
    def add_transaction(self, request, pk=None):
        """Add a transaction to the reconciliation and recalculate."""
        reconciliation = self.get_object()
        transaction_id = request.data.get("transaction_id")

        try:
            tx = BankTransaction.objects.get(id=transaction_id)
        except BankTransaction.DoesNotExist:
            return Response(
                {"error": "Transaction not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        tx.status = BankTransaction.Status.RECONCILED
        tx.save(update_fields=["status"])

        reconciliation.transactions.add(tx)
        reconciliation.calculate_cleared_balance()

        return Response(ReconciliationSerializer(reconciliation).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Complete the reconciliation if balanced."""
        reconciliation = self.get_object()
        reconciliation.calculate_cleared_balance()

        if reconciliation.difference != Decimal("0.00"):
            return Response(
                {
                    "error": f"Reconciliation is not balanced. Difference: {reconciliation.difference}",
                    "difference": str(reconciliation.difference),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            reconciliation.status = Reconciliation.Status.COMPLETED
            reconciliation.reconciled_by = request.user
            reconciliation.completed_at = timezone.now()
            reconciliation.save()

            bank_account = reconciliation.bank_account
            bank_account.last_reconciled_date = reconciliation.statement_date
            bank_account.last_reconciled_balance = reconciliation.statement_balance
            bank_account.save(update_fields=[
                "last_reconciled_date", "last_reconciled_balance"
            ])

        return Response({
            "message": "Reconciliation completed successfully.",
            "data": ReconciliationSerializer(reconciliation).data,
        })
