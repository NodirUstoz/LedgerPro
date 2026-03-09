"""
BankAccount, BankTransaction, and Reconciliation models.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from auditlog.registry import auditlog


class BankAccount(models.Model):
    """Bank account linked to a ledger account."""

    class AccountType(models.TextChoices):
        CHECKING = "checking", "Checking"
        SAVINGS = "savings", "Savings"
        CREDIT_CARD = "credit_card", "Credit Card"
        MONEY_MARKET = "money_market", "Money Market"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "accounts.Company", on_delete=models.CASCADE, related_name="bank_accounts"
    )
    name = models.CharField(max_length=255)
    bank_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50)
    routing_number = models.CharField(max_length=50, blank=True)
    account_type = models.CharField(
        max_length=20, choices=AccountType.choices, default=AccountType.CHECKING
    )
    currency = models.CharField(max_length=3, default="USD")
    current_balance = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    last_reconciled_date = models.DateField(null=True, blank=True)
    last_reconciled_balance = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )

    # Link to chart of accounts
    ledger_account = models.OneToOneField(
        "ledger.Account",
        on_delete=models.PROTECT,
        related_name="bank_account",
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bank_accounts"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.bank_name})"

    @property
    def masked_account_number(self):
        if len(self.account_number) > 4:
            return "****" + self.account_number[-4:]
        return self.account_number


class BankTransaction(models.Model):
    """Individual bank transaction (imported or manual)."""

    class TransactionType(models.TextChoices):
        DEPOSIT = "deposit", "Deposit"
        WITHDRAWAL = "withdrawal", "Withdrawal"
        TRANSFER = "transfer", "Transfer"
        FEE = "fee", "Fee"
        INTEREST = "interest", "Interest"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CLEARED = "cleared", "Cleared"
        RECONCILED = "reconciled", "Reconciled"
        VOIDED = "voided", "Voided"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank_account = models.ForeignKey(
        BankAccount, on_delete=models.CASCADE, related_name="transactions"
    )
    date = models.DateField(db_index=True)
    description = models.CharField(max_length=500)
    reference = models.CharField(max_length=100, blank=True)
    transaction_type = models.CharField(
        max_length=20, choices=TransactionType.choices
    )
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    running_balance = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    payee = models.CharField(max_length=255, blank=True)
    category = models.ForeignKey(
        "expenses.ExpenseCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # Matching to journal entries
    journal_entry = models.ForeignKey(
        "ledger.JournalEntry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bank_transactions",
    )
    matched_journal_line = models.ForeignKey(
        "ledger.JournalLine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bank_transactions",
    )

    # Import metadata
    external_id = models.CharField(
        max_length=255, blank=True, help_text="ID from bank import file."
    )
    import_batch = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bank_transactions"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.date} - {self.description} - {self.amount}"


class Reconciliation(models.Model):
    """Bank reconciliation session."""

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        ABANDONED = "abandoned", "Abandoned"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank_account = models.ForeignKey(
        BankAccount, on_delete=models.CASCADE, related_name="reconciliations"
    )
    statement_date = models.DateField()
    statement_balance = models.DecimalField(max_digits=18, decimal_places=2)
    opening_balance = models.DecimalField(max_digits=18, decimal_places=2)
    cleared_balance = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    difference = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IN_PROGRESS
    )
    transactions = models.ManyToManyField(
        BankTransaction, blank=True, related_name="reconciliations"
    )
    notes = models.TextField(blank=True)
    reconciled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reconciliations"
        ordering = ["-statement_date"]

    def __str__(self):
        return f"Reconciliation {self.bank_account.name} - {self.statement_date}"

    def calculate_cleared_balance(self):
        """Calculate the sum of all cleared transactions."""
        total = self.transactions.filter(
            status=BankTransaction.Status.RECONCILED
        ).aggregate(total=models.Sum("amount"))["total"] or Decimal("0.00")
        self.cleared_balance = self.opening_balance + total
        self.difference = self.statement_balance - self.cleared_balance
        self.save(update_fields=["cleared_balance", "difference"])


auditlog.register(BankAccount)
auditlog.register(BankTransaction)
auditlog.register(Reconciliation)
