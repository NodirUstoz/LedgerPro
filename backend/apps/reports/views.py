"""
Views for the reports app -- financial statement generation and saved reports.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Q, Sum
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import Company
from apps.ledger.models import Account, AccountType, JournalEntry, JournalLine

from .models import ReportSchedule, SavedReport
from .serializers import (
    BalanceSheetRequestSerializer,
    CashFlowRequestSerializer,
    IncomeStatementRequestSerializer,
    ReportScheduleSerializer,
    SavedReportListSerializer,
    SavedReportSerializer,
)


def _get_company_or_error(request, company_id):
    """Validate and return a company the user has access to."""
    try:
        return Company.objects.get(
            id=company_id,
            memberships__user=request.user,
            memberships__is_active=True,
        )
    except Company.DoesNotExist:
        return None


def _account_balance(account, start_date=None, end_date=None):
    """Calculate account balance from posted journal lines within a date range."""
    lines = JournalLine.objects.filter(
        account=account,
        journal_entry__status=JournalEntry.Status.POSTED,
    )
    if start_date:
        lines = lines.filter(journal_entry__date__gte=start_date)
    if end_date:
        lines = lines.filter(journal_entry__date__lte=end_date)

    totals = lines.aggregate(
        debit=Sum("base_debit_amount"),
        credit=Sum("base_credit_amount"),
    )
    debit = totals["debit"] or Decimal("0.00")
    credit = totals["credit"] or Decimal("0.00")

    if account.normal_balance == "debit":
        return debit - credit
    return credit - debit


class FinancialStatementViewSet(viewsets.ViewSet):
    """Generate financial statements (Income Statement, Balance Sheet, Cash Flow)."""

    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"])
    def income_statement(self, request):
        """
        Generate an income statement (profit & loss) for a date range.
        Query params: company, start_date, end_date, compare_prior_period
        """
        company_id = request.query_params.get("company")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date", date.today().isoformat())
        compare = request.query_params.get("compare_prior_period", "false").lower() == "true"

        if not company_id or not start_date:
            return Response(
                {"error": "company and start_date query params are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        company = _get_company_or_error(request, company_id)
        if not company:
            return Response(
                {"error": "Company not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

        revenue_accounts = Account.objects.filter(
            company=company, account_type=AccountType.REVENUE, is_active=True
        ).order_by("code")

        expense_accounts = Account.objects.filter(
            company=company, account_type=AccountType.EXPENSE, is_active=True
        ).order_by("code")

        revenue_items = []
        total_revenue = Decimal("0.00")
        for acct in revenue_accounts:
            bal = _account_balance(acct, start, end)
            revenue_items.append({
                "account_code": acct.code,
                "account_name": acct.name,
                "sub_type": acct.sub_type,
                "amount": str(bal),
            })
            total_revenue += bal

        expense_items = []
        total_expenses = Decimal("0.00")
        for acct in expense_accounts:
            bal = _account_balance(acct, start, end)
            expense_items.append({
                "account_code": acct.code,
                "account_name": acct.name,
                "sub_type": acct.sub_type,
                "amount": str(bal),
            })
            total_expenses += bal

        net_income = total_revenue - total_expenses

        result = {
            "company": company.name,
            "period_start": start_date,
            "period_end": end_date,
            "revenue": {
                "items": revenue_items,
                "total": str(total_revenue),
            },
            "expenses": {
                "items": expense_items,
                "total": str(total_expenses),
            },
            "net_income": str(net_income),
        }

        if compare:
            period_length = (end - start).days
            prior_end = start - timedelta(days=1)
            prior_start = prior_end - timedelta(days=period_length)

            prior_revenue = Decimal("0.00")
            for acct in revenue_accounts:
                prior_revenue += _account_balance(acct, prior_start, prior_end)

            prior_expenses = Decimal("0.00")
            for acct in expense_accounts:
                prior_expenses += _account_balance(acct, prior_start, prior_end)

            result["prior_period"] = {
                "period_start": prior_start.isoformat(),
                "period_end": prior_end.isoformat(),
                "total_revenue": str(prior_revenue),
                "total_expenses": str(prior_expenses),
                "net_income": str(prior_revenue - prior_expenses),
            }

        return Response(result)

    @action(detail=False, methods=["get"])
    def balance_sheet(self, request):
        """
        Generate a balance sheet as of a specific date.
        Query params: company, as_of_date
        """
        company_id = request.query_params.get("company")
        as_of = request.query_params.get("as_of_date", date.today().isoformat())

        if not company_id:
            return Response(
                {"error": "company query param is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        company = _get_company_or_error(request, company_id)
        if not company:
            return Response(
                {"error": "Company not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        as_of_date = date.fromisoformat(as_of)

        sections = {}
        for acct_type in [AccountType.ASSET, AccountType.LIABILITY, AccountType.EQUITY]:
            accounts = Account.objects.filter(
                company=company, account_type=acct_type, is_active=True
            ).order_by("code")

            items = []
            section_total = Decimal("0.00")
            for acct in accounts:
                bal = acct.opening_balance + _account_balance(acct, end_date=as_of_date)
                items.append({
                    "account_code": acct.code,
                    "account_name": acct.name,
                    "sub_type": acct.sub_type,
                    "balance": str(bal),
                })
                section_total += bal

            sections[acct_type] = {
                "items": items,
                "total": str(section_total),
            }

        total_assets = Decimal(sections[AccountType.ASSET]["total"])
        total_liabilities = Decimal(sections[AccountType.LIABILITY]["total"])
        total_equity = Decimal(sections[AccountType.EQUITY]["total"])

        return Response({
            "company": company.name,
            "as_of_date": as_of,
            "assets": sections[AccountType.ASSET],
            "liabilities": sections[AccountType.LIABILITY],
            "equity": sections[AccountType.EQUITY],
            "total_liabilities_and_equity": str(total_liabilities + total_equity),
            "is_balanced": total_assets == (total_liabilities + total_equity),
        })

    @action(detail=False, methods=["get"])
    def cash_flow(self, request):
        """
        Generate a cash flow statement for a date range.
        Query params: company, start_date, end_date
        """
        company_id = request.query_params.get("company")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date", date.today().isoformat())

        if not company_id or not start_date:
            return Response(
                {"error": "company and start_date query params are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        company = _get_company_or_error(request, company_id)
        if not company:
            return Response(
                {"error": "Company not found or access denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

        # Operating activities: net income + non-cash adjustments
        revenue_total = Decimal("0.00")
        for acct in Account.objects.filter(
            company=company, account_type=AccountType.REVENUE, is_active=True
        ):
            revenue_total += _account_balance(acct, start, end)

        expense_total = Decimal("0.00")
        for acct in Account.objects.filter(
            company=company, account_type=AccountType.EXPENSE, is_active=True
        ):
            expense_total += _account_balance(acct, start, end)

        net_income = revenue_total - expense_total

        # Change in current assets/liabilities
        ar_change = Decimal("0.00")
        for acct in Account.objects.filter(
            company=company, sub_type="accounts_receivable", is_active=True
        ):
            ar_change += _account_balance(acct, start, end)

        ap_change = Decimal("0.00")
        for acct in Account.objects.filter(
            company=company, sub_type="accounts_payable", is_active=True
        ):
            ap_change += _account_balance(acct, start, end)

        operating = net_income - ar_change + ap_change

        # Investing: fixed asset changes
        investing = Decimal("0.00")
        for acct in Account.objects.filter(
            company=company, sub_type="fixed_asset", is_active=True
        ):
            investing -= _account_balance(acct, start, end)

        # Financing: equity and long-term liabilities changes
        financing = Decimal("0.00")
        for acct in Account.objects.filter(
            company=company,
            sub_type__in=["owners_equity", "retained_earnings", "long_term_liability"],
            is_active=True,
        ):
            financing += _account_balance(acct, start, end)

        net_change = operating + investing + financing

        # Opening cash
        opening_cash = Decimal("0.00")
        for acct in Account.objects.filter(
            company=company, sub_type="bank", is_active=True
        ):
            opening_cash += acct.opening_balance + _account_balance(
                acct, end_date=start - timedelta(days=1)
            )

        return Response({
            "company": company.name,
            "period_start": start_date,
            "period_end": end_date,
            "operating_activities": {
                "net_income": str(net_income),
                "ar_change": str(ar_change),
                "ap_change": str(ap_change),
                "total": str(operating),
            },
            "investing_activities": {
                "total": str(investing),
            },
            "financing_activities": {
                "total": str(financing),
            },
            "net_change_in_cash": str(net_change),
            "opening_cash_balance": str(opening_cash),
            "closing_cash_balance": str(opening_cash + net_change),
        })


class SavedReportViewSet(viewsets.ModelViewSet):
    """CRUD operations for saved reports."""

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["created_at", "name", "report_type"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return SavedReportListSerializer
        return SavedReportSerializer

    def get_queryset(self):
        qs = SavedReport.objects.filter(
            company__memberships__user=self.request.user,
            company__memberships__is_active=True,
        )

        company_id = self.request.query_params.get("company")
        if company_id:
            qs = qs.filter(company_id=company_id)

        report_type = self.request.query_params.get("report_type")
        if report_type:
            qs = qs.filter(report_type=report_type)

        favorites = self.request.query_params.get("favorites")
        if favorites and favorites.lower() == "true":
            qs = qs.filter(is_favorite=True)

        return qs.distinct()

    def perform_create(self, serializer):
        serializer.save(generated_by=self.request.user)

    @action(detail=True, methods=["post"])
    def toggle_favorite(self, request, pk=None):
        """Toggle the favorite status of a saved report."""
        report = self.get_object()
        report.is_favorite = not report.is_favorite
        report.save(update_fields=["is_favorite"])
        return Response({
            "is_favorite": report.is_favorite,
            "message": "Favorite toggled.",
        })


class ReportScheduleViewSet(viewsets.ModelViewSet):
    """CRUD operations for report schedules."""

    serializer_class = ReportScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ReportSchedule.objects.filter(
            company__memberships__user=self.request.user,
            company__memberships__is_active=True,
        )

        company_id = self.request.query_params.get("company")
        if company_id:
            qs = qs.filter(company_id=company_id)

        return qs.distinct()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
