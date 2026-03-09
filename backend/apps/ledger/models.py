"""
Chart of Accounts, Account, JournalEntry, and JournalLine models.
Core double-entry bookkeeping data structures.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from auditlog.registry import auditlog


class AccountType(models.TextChoices):
    """Standard accounting classifications."""
    ASSET = "asset", "Asset"
    LIABILITY = "liability", "Liability"
    EQUITY = "equity", "Equity"
    REVENUE = "revenue", "Revenue"
    EXPENSE = "expense", "Expense"


class AccountSubType(models.TextChoices):
    """Sub-classifications for accounts."""
    # Assets
    CURRENT_ASSET = "current_asset", "Current Asset"
    FIXED_ASSET = "fixed_asset", "Fixed Asset"
    OTHER_ASSET = "other_asset", "Other Asset"
    BANK = "bank", "Bank"
    ACCOUNTS_RECEIVABLE = "accounts_receivable", "Accounts Receivable"
    INVENTORY = "inventory", "Inventory"
    PREPAID = "prepaid", "Prepaid Expense"
    # Liabilities
    CURRENT_LIABILITY = "current_liability", "Current Liability"
    LONG_TERM_LIABILITY = "long_term_liability", "Long-Term Liability"
    ACCOUNTS_PAYABLE = "accounts_payable", "Accounts Payable"
    CREDIT_CARD = "credit_card", "Credit Card"
    TAX_PAYABLE = "tax_payable", "Tax Payable"
    # Equity
    OWNERS_EQUITY = "owners_equity", "Owner's Equity"
    RETAINED_EARNINGS = "retained_earnings", "Retained Earnings"
    # Revenue
    OPERATING_REVENUE = "operating_revenue", "Operating Revenue"
    OTHER_INCOME = "other_income", "Other Income"
    # Expense
    OPERATING_EXPENSE = "operating_expense", "Operating Expense"
    COST_OF_GOODS = "cost_of_goods", "Cost of Goods Sold"
    PAYROLL_EXPENSE = "payroll_expense", "Payroll Expense"
    OTHER_EXPENSE = "other_expense", "Other Expense"


class NormalBalance(models.TextChoices):
    """Normal balance side for accounts."""
    DEBIT = "debit", "Debit"
    CREDIT = "credit", "Credit"


class Account(models.Model):
    """
    Chart of Accounts entry. Represents a single account in the
    hierarchical chart of accounts for a company.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="accounts",
    )
    code = models.CharField(
        max_length=20,
        help_text="Account code (e.g., 1000, 1100, 2000)",
        db_index=True,
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
    )
    sub_type = models.CharField(
        max_length=30,
        choices=AccountSubType.choices,
        blank=True,
    )
    normal_balance = models.CharField(
        max_length=10,
        choices=NormalBalance.choices,
        help_text="Debit-normal for assets/expenses, credit-normal for liabilities/equity/revenue.",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    currency = models.CharField(max_length=3, default="USD")
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(
        default=False,
        help_text="System accounts cannot be deleted.",
    )
    tax_rate = models.ForeignKey(
        "tax.TaxRate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accounts",
    )
    opening_balance = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    current_balance = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_chart"
        ordering = ["code"]
        unique_together = ("company", "code")
        verbose_name = "account"
        verbose_name_plural = "chart of accounts"

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.normal_balance:
            if self.account_type in (AccountType.ASSET, AccountType.EXPENSE):
                self.normal_balance = NormalBalance.DEBIT
            else:
                self.normal_balance = NormalBalance.CREDIT
        super().save(*args, **kwargs)

    @property
    def full_path(self):
        """Return the full hierarchical path of the account."""
        parts = [self.name]
        current = self.parent
        while current:
            parts.insert(0, current.name)
            current = current.parent
        return " > ".join(parts)

    def recalculate_balance(self):
        """Recalculate the current balance from all posted journal lines."""
        debit_sum = self.journal_lines.filter(
            journal_entry__status=JournalEntry.Status.POSTED
        ).aggregate(total=models.Sum("debit_amount"))["total"] or Decimal("0.00")

        credit_sum = self.journal_lines.filter(
            journal_entry__status=JournalEntry.Status.POSTED
        ).aggregate(total=models.Sum("credit_amount"))["total"] or Decimal("0.00")

        if self.normal_balance == NormalBalance.DEBIT:
            self.current_balance = self.opening_balance + debit_sum - credit_sum
        else:
            self.current_balance = self.opening_balance + credit_sum - debit_sum

        self.save(update_fields=["current_balance"])
        return self.current_balance


class JournalEntry(models.Model):
    """
    A journal entry representing a complete accounting transaction.
    Must have balanced debit and credit lines (double-entry).
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending Approval"
        POSTED = "posted", "Posted"
        VOIDED = "voided", "Voided"

    class EntryType(models.TextChoices):
        STANDARD = "standard", "Standard"
        ADJUSTING = "adjusting", "Adjusting"
        CLOSING = "closing", "Closing"
        REVERSING = "reversing", "Reversing"
        OPENING = "opening", "Opening"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="journal_entries",
    )
    entry_number = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        help_text="Auto-generated sequential entry number.",
    )
    date = models.DateField(db_index=True)
    description = models.TextField(help_text="Memo / description of the transaction.")
    reference = models.CharField(
        max_length=100, blank=True,
        help_text="External reference (invoice #, check #, etc.)",
    )
    entry_type = models.CharField(
        max_length=20, choices=EntryType.choices, default=EntryType.STANDARD
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    fiscal_year = models.ForeignKey(
        "accounts.FiscalYear",
        on_delete=models.PROTECT,
        related_name="journal_entries",
        null=True,
        blank=True,
    )
    currency = models.CharField(max_length=3, default="USD")
    exchange_rate = models.DecimalField(
        max_digits=12, decimal_places=6, default=Decimal("1.000000"),
        help_text="Exchange rate to base currency at transaction date.",
    )
    attachments = models.JSONField(
        default=list, blank=True,
        help_text="List of attachment file paths.",
    )
    source_module = models.CharField(
        max_length=50, blank=True,
        help_text="Module that created this entry (invoicing, expenses, etc.)",
    )
    source_id = models.UUIDField(
        null=True, blank=True,
        help_text="ID of the source document.",
    )
    reversing_entry = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reversed_by",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_journal_entries",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_journal_entries",
    )
    posted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "journal_entries"
        ordering = ["-date", "-entry_number"]
        verbose_name = "journal entry"
        verbose_name_plural = "journal entries"

    def __str__(self):
        return f"{self.entry_number} - {self.date} - {self.description[:50]}"

    @property
    def total_debit(self):
        return self.lines.aggregate(
            total=models.Sum("debit_amount")
        )["total"] or Decimal("0.00")

    @property
    def total_credit(self):
        return self.lines.aggregate(
            total=models.Sum("credit_amount")
        )["total"] or Decimal("0.00")

    @property
    def is_balanced(self):
        return self.total_debit == self.total_credit


class JournalLine(models.Model):
    """
    Individual line within a journal entry.
    Each line debits or credits a specific account.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="journal_lines",
    )
    description = models.CharField(max_length=500, blank=True)
    debit_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    credit_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    currency = models.CharField(max_length=3, default="USD")
    exchange_rate = models.DecimalField(
        max_digits=12, decimal_places=6, default=Decimal("1.000000")
    )
    base_debit_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00"),
        help_text="Debit amount in base currency.",
    )
    base_credit_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00"),
        help_text="Credit amount in base currency.",
    )
    tax_rate = models.ForeignKey(
        "tax.TaxRate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    tax_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    reconciled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "journal_lines"
        ordering = ["created_at"]
        verbose_name = "journal line"

    def __str__(self):
        if self.debit_amount > 0:
            return f"DR {self.account.code} {self.debit_amount}"
        return f"CR {self.account.code} {self.credit_amount}"

    def save(self, *args, **kwargs):
        # Compute base currency amounts
        self.base_debit_amount = self.debit_amount * self.exchange_rate
        self.base_credit_amount = self.credit_amount * self.exchange_rate
        super().save(*args, **kwargs)


class ExchangeRate(models.Model):
    """Historical exchange rate storage."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    base_currency = models.CharField(max_length=3, default="USD")
    target_currency = models.CharField(max_length=3)
    rate = models.DecimalField(max_digits=12, decimal_places=6)
    date = models.DateField(db_index=True)
    source = models.CharField(max_length=100, default="api")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "exchange_rates"
        unique_together = ("base_currency", "target_currency", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.base_currency}/{self.target_currency} = {self.rate} ({self.date})"


# Register models with audit log
auditlog.register(Account)
auditlog.register(JournalEntry)
auditlog.register(JournalLine)
