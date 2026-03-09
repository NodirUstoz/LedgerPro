"""
Expense, ExpenseCategory, and Receipt models.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from auditlog.registry import auditlog


class ExpenseCategory(models.Model):
    """Category for organizing expenses."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "accounts.Company", on_delete=models.CASCADE, related_name="expense_categories"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="subcategories"
    )
    default_account = models.ForeignKey(
        "ledger.Account",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Default expense account for this category.",
    )
    budget_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00"),
        help_text="Monthly budget for this category.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "expense_categories"
        ordering = ["name"]
        unique_together = ("company", "name")
        verbose_name_plural = "expense categories"

    def __str__(self):
        return self.name


class Vendor(models.Model):
    """Vendor / supplier for expenses."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "accounts.Company", on_delete=models.CASCADE, related_name="vendors"
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    payment_terms = models.PositiveIntegerField(default=30)
    currency = models.CharField(max_length=3, default="USD")
    default_category = models.ForeignKey(
        ExpenseCategory, on_delete=models.SET_NULL, null=True, blank=True
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vendors"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Expense(models.Model):
    """Individual expense record."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending Approval"
        APPROVED = "approved", "Approved"
        PAID = "paid", "Paid"
        REJECTED = "rejected", "Rejected"
        VOIDED = "voided", "Voided"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "accounts.Company", on_delete=models.CASCADE, related_name="expenses"
    )
    expense_number = models.CharField(max_length=30, unique=True, db_index=True)
    vendor = models.ForeignKey(
        Vendor, on_delete=models.SET_NULL, null=True, blank=True, related_name="expenses"
    )
    category = models.ForeignKey(
        ExpenseCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="expenses"
    )
    date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    description = models.TextField()
    amount = models.DecimalField(
        max_digits=18, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    tax_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    total_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    currency = models.CharField(max_length=3, default="USD")
    exchange_rate = models.DecimalField(
        max_digits=12, decimal_places=6, default=Decimal("1.000000")
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    payment_method = models.CharField(max_length=50, blank=True)
    reference = models.CharField(max_length=100, blank=True, help_text="Receipt/bill number.")
    notes = models.TextField(blank=True)
    is_billable = models.BooleanField(
        default=False, help_text="Can be billed to a customer."
    )
    billable_customer = models.ForeignKey(
        "invoicing.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="billable_expenses",
    )

    # Accounting link
    expense_account = models.ForeignKey(
        "ledger.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="expenses",
    )
    payment_account = models.ForeignKey(
        "ledger.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="expense_payments",
        help_text="Account used for payment (bank, cash, credit card).",
    )
    journal_entry = models.ForeignKey(
        "ledger.JournalEntry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
    )

    tax_rate = models.ForeignKey(
        "tax.TaxRate", on_delete=models.SET_NULL, null=True, blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_expenses"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="approved_expenses"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "expenses"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.expense_number} - {self.description[:50]}"

    def save(self, *args, **kwargs):
        self.total_amount = self.amount + self.tax_amount
        super().save(*args, **kwargs)


class Receipt(models.Model):
    """Uploaded receipt or document for an expense."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense = models.ForeignKey(
        Expense, on_delete=models.CASCADE, related_name="receipts"
    )
    file = models.FileField(upload_to="receipts/%Y/%m/")
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="File size in bytes.")
    mime_type = models.CharField(max_length=100)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "receipts"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.filename


auditlog.register(Expense)
auditlog.register(ExpenseCategory)
