"""
Report templates and saved report models.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models


class SavedReport(models.Model):
    """A saved/generated financial report for archival or re-generation."""

    class ReportType(models.TextChoices):
        INCOME_STATEMENT = "income_statement", "Income Statement"
        BALANCE_SHEET = "balance_sheet", "Balance Sheet"
        CASH_FLOW = "cash_flow", "Cash Flow Statement"
        TRIAL_BALANCE = "trial_balance", "Trial Balance"
        GENERAL_LEDGER = "general_ledger", "General Ledger"
        ACCOUNTS_RECEIVABLE_AGING = "ar_aging", "Accounts Receivable Aging"
        ACCOUNTS_PAYABLE_AGING = "ap_aging", "Accounts Payable Aging"
        TAX_SUMMARY = "tax_summary", "Tax Summary"
        EXPENSE_SUMMARY = "expense_summary", "Expense Summary"
        BUDGET_VS_ACTUAL = "budget_vs_actual", "Budget vs. Actual"
        CUSTOM = "custom", "Custom Report"

    class FileFormat(models.TextChoices):
        PDF = "pdf", "PDF"
        XLSX = "xlsx", "Excel"
        CSV = "csv", "CSV"
        JSON = "json", "JSON"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "accounts.Company", on_delete=models.CASCADE, related_name="saved_reports"
    )
    name = models.CharField(max_length=255)
    report_type = models.CharField(
        max_length=30, choices=ReportType.choices
    )
    parameters = models.JSONField(
        default=dict, blank=True,
        help_text="Parameters used to generate this report (date range, filters, etc.).",
    )
    data = models.JSONField(
        default=dict, blank=True,
        help_text="The raw report data as JSON.",
    )
    file = models.FileField(
        upload_to="reports/%Y/%m/", blank=True, null=True,
        help_text="Exported file if generated.",
    )
    file_format = models.CharField(
        max_length=10, choices=FileFormat.choices, blank=True
    )
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="generated_reports",
    )
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "saved_reports"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"


class ReportSchedule(models.Model):
    """Scheduled recurring report generation."""

    class Frequency(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "accounts.Company", on_delete=models.CASCADE, related_name="report_schedules"
    )
    report_type = models.CharField(
        max_length=30, choices=SavedReport.ReportType.choices
    )
    name = models.CharField(max_length=255)
    frequency = models.CharField(
        max_length=20, choices=Frequency.choices
    )
    parameters = models.JSONField(default=dict, blank=True)
    recipients = models.JSONField(
        default=list, blank=True,
        help_text="List of email addresses to send the report to.",
    )
    file_format = models.CharField(
        max_length=10,
        choices=SavedReport.FileFormat.choices,
        default=SavedReport.FileFormat.PDF,
    )
    is_active = models.BooleanField(default=True)
    last_generated = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "report_schedules"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"
