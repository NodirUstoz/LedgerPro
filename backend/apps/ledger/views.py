"""
Views for ledger app.
"""

from datetime import date

from django.db.models import Q
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Account, ExchangeRate, JournalEntry, JournalLine
from .serializers import (
    AccountSerializer,
    AccountTreeSerializer,
    ExchangeRateSerializer,
    JournalEntryListSerializer,
    JournalEntrySerializer,
)
from .services import (
    DoubleEntryError,
    FiscalPeriodError,
    get_trial_balance,
    post_journal_entry,
    reverse_journal_entry,
    void_journal_entry,
)


class AccountViewSet(viewsets.ModelViewSet):
    """CRUD operations for the chart of accounts."""

    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["code", "name", "description"]
    ordering_fields = ["code", "name", "account_type", "current_balance"]
    ordering = ["code"]

    def get_queryset(self):
        qs = Account.objects.filter(
            company__memberships__user=self.request.user,
            company__memberships__is_active=True,
        ).select_related("parent", "tax_rate")

        company_id = self.request.query_params.get("company")
        if company_id:
            qs = qs.filter(company_id=company_id)

        account_type = self.request.query_params.get("type")
        if account_type:
            qs = qs.filter(account_type=account_type)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")

        return qs.distinct()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["company"] = self.request.query_params.get("company")
        return context

    @action(detail=False, methods=["get"])
    def tree(self, request):
        """Return the chart of accounts as a hierarchical tree."""
        company_id = request.query_params.get("company")
        if not company_id:
            return Response(
                {"error": "company query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        root_accounts = Account.objects.filter(
            company_id=company_id,
            parent__isnull=True,
            is_active=True,
        ).order_by("code")

        serializer = AccountTreeSerializer(root_accounts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def ledger(self, request, pk=None):
        """Return all journal lines for a specific account (account ledger)."""
        account = self.get_object()
        lines = JournalLine.objects.filter(
            account=account,
            journal_entry__status=JournalEntry.Status.POSTED,
        ).select_related("journal_entry").order_by("journal_entry__date")

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if start_date:
            lines = lines.filter(journal_entry__date__gte=start_date)
        if end_date:
            lines = lines.filter(journal_entry__date__lte=end_date)

        from .serializers import JournalLineSerializer
        from utils.pagination import StandardResultsSetPagination

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(lines, request)
        serializer = JournalLineSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        account = self.get_object()
        if account.is_system:
            return Response(
                {"error": "System accounts cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if account.journal_lines.exists():
            return Response(
                {"error": "Cannot delete account with existing transactions. Deactivate it instead."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class JournalEntryViewSet(viewsets.ModelViewSet):
    """CRUD operations for journal entries."""

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["entry_number", "description", "reference"]
    ordering_fields = ["date", "entry_number", "created_at"]
    ordering = ["-date", "-entry_number"]

    def get_serializer_class(self):
        if self.action == "list":
            return JournalEntryListSerializer
        return JournalEntrySerializer

    def get_queryset(self):
        qs = JournalEntry.objects.filter(
            company__memberships__user=self.request.user,
            company__memberships__is_active=True,
        ).select_related("created_by", "approved_by", "fiscal_year")

        company_id = self.request.query_params.get("company")
        if company_id:
            qs = qs.filter(company_id=company_id)

        entry_status = self.request.query_params.get("status")
        if entry_status:
            qs = qs.filter(status=entry_status)

        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)

        entry_type = self.request.query_params.get("entry_type")
        if entry_type:
            qs = qs.filter(entry_type=entry_type)

        return qs.distinct()

    @action(detail=True, methods=["post"])
    def post_entry(self, request, pk=None):
        """Post a draft journal entry."""
        entry = self.get_object()
        try:
            post_journal_entry(entry, request.user)
            return Response(
                JournalEntrySerializer(entry, context={"request": request}).data
            )
        except (DoubleEntryError, FiscalPeriodError) as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        """Void a posted journal entry."""
        entry = self.get_object()
        try:
            void_journal_entry(entry, request.user)
            return Response(
                JournalEntrySerializer(entry, context={"request": request}).data
            )
        except DoubleEntryError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["post"])
    def reverse(self, request, pk=None):
        """Create a reversing entry for a posted journal entry."""
        entry = self.get_object()
        reversal_date = request.data.get("reversal_date", date.today().isoformat())
        try:
            reversal = reverse_journal_entry(
                entry,
                date.fromisoformat(reversal_date),
                request.user,
            )
            return Response(
                JournalEntrySerializer(reversal, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        except DoubleEntryError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        entry = self.get_object()
        if entry.status == JournalEntry.Status.POSTED:
            return Response(
                {"error": "Posted entries cannot be deleted. Void or reverse instead."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class TrialBalanceView(viewsets.ViewSet):
    """Generate trial balance reports."""

    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        company_id = request.query_params.get("company")
        as_of = request.query_params.get("as_of_date", date.today().isoformat())

        if not company_id:
            return Response(
                {"error": "company query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.accounts.models import Company
        try:
            company = Company.objects.get(
                id=company_id,
                memberships__user=request.user,
                memberships__is_active=True,
            )
        except Company.DoesNotExist:
            return Response(
                {"error": "Company not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        result = get_trial_balance(company, date.fromisoformat(as_of))
        return Response(result)


class ExchangeRateViewSet(viewsets.ModelViewSet):
    """CRUD operations for exchange rates."""

    serializer_class = ExchangeRateSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering = ["-date"]

    def get_queryset(self):
        qs = ExchangeRate.objects.all()
        base = self.request.query_params.get("base")
        target = self.request.query_params.get("target")
        if base:
            qs = qs.filter(base_currency=base.upper())
        if target:
            qs = qs.filter(target_currency=target.upper())
        return qs
