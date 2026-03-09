"""
Invoice, InvoiceLine, Payment, and CreditNote models.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from auditlog.registry import auditlog


class Customer(models.Model):
    """Customer / client entity for invoicing."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "accounts.Company", on_delete=models.CASCADE, related_name="customers"
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    billing_address = models.TextField(blank=True)
    shipping_address = models.TextField(blank=True)
    payment_terms = models.PositiveIntegerField(
        default=30, help_text="Default payment terms in days."
    )
    credit_limit = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    currency = models.CharField(max_length=3, default="USD")
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "customers"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def outstanding_balance(self):
        return self.invoices.filter(
            status__in=[Invoice.Status.SENT, Invoice.Status.PARTIALLY_PAID, Invoice.Status.OVERDUE]
        ).aggregate(total=models.Sum("balance_due"))["total"] or Decimal("0.00")


class Invoice(models.Model):
    """Sales invoice."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        PARTIALLY_PAID = "partially_paid", "Partially Paid"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"
        VOIDED = "voided", "Voided"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "accounts.Company", on_delete=models.CASCADE, related_name="invoices"
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name="invoices"
    )
    invoice_number = models.CharField(max_length=30, unique=True, db_index=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    issue_date = models.DateField()
    due_date = models.DateField()
    currency = models.CharField(max_length=3, default="USD")
    exchange_rate = models.DecimalField(
        max_digits=12, decimal_places=6, default=Decimal("1.000000")
    )
    subtotal = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    tax_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    discount_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    total_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    amount_paid = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    balance_due = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    notes = models.TextField(blank=True)
    terms = models.TextField(blank=True)
    footer = models.TextField(blank=True)

    # Accounting link
    journal_entry = models.ForeignKey(
        "ledger.JournalEntry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )
    accounts_receivable = models.ForeignKey(
        "ledger.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ar_invoices",
        help_text="Accounts Receivable account for this invoice.",
    )
    revenue_account = models.ForeignKey(
        "ledger.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revenue_invoices",
        help_text="Default revenue account.",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_invoices"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "invoices"
        ordering = ["-issue_date", "-invoice_number"]

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.customer.name}"

    def recalculate_totals(self):
        """Recalculate invoice totals from lines."""
        lines = self.lines.all()
        self.subtotal = sum(line.line_total for line in lines)
        self.tax_amount = sum(line.tax_amount for line in lines)
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        self.balance_due = self.total_amount - self.amount_paid
        self.save(update_fields=[
            "subtotal", "tax_amount", "total_amount", "balance_due"
        ])

    def update_payment_status(self):
        """Update invoice status based on payments received."""
        if self.amount_paid >= self.total_amount:
            self.status = self.Status.PAID
        elif self.amount_paid > 0:
            self.status = self.Status.PARTIALLY_PAID
        self.balance_due = self.total_amount - self.amount_paid
        self.save(update_fields=["status", "balance_due", "amount_paid"])


class InvoiceLine(models.Model):
    """Individual line item on an invoice."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="lines"
    )
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(
        max_digits=12, decimal_places=4, default=Decimal("1.0000"),
        validators=[MinValueValidator(Decimal("0.0001"))],
    )
    unit_price = models.DecimalField(
        max_digits=18, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))]
    )
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00")
    )
    tax_rate = models.ForeignKey(
        "tax.TaxRate", on_delete=models.SET_NULL, null=True, blank=True
    )
    tax_amount = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    line_total = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    account = models.ForeignKey(
        "ledger.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Revenue account for this line.",
    )
    order_index = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "invoice_lines"
        ordering = ["order_index"]

    def __str__(self):
        return f"{self.description} x{self.quantity}"

    def save(self, *args, **kwargs):
        subtotal = self.quantity * self.unit_price
        discount = subtotal * (self.discount_percent / Decimal("100.00"))
        self.line_total = subtotal - discount
        if self.tax_rate:
            self.tax_amount = self.line_total * (self.tax_rate.rate / Decimal("100.00"))
        super().save(*args, **kwargs)


class Payment(models.Model):
    """Payment received against an invoice."""

    class Method(models.TextChoices):
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"
        CREDIT_CARD = "credit_card", "Credit Card"
        CHECK = "check", "Check"
        CASH = "cash", "Cash"
        PAYPAL = "paypal", "PayPal"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "accounts.Company", on_delete=models.CASCADE, related_name="payments"
    )
    invoice = models.ForeignKey(
        Invoice, on_delete=models.PROTECT, related_name="payments"
    )
    payment_number = models.CharField(max_length=30, unique=True)
    date = models.DateField()
    amount = models.DecimalField(
        max_digits=18, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    currency = models.CharField(max_length=3, default="USD")
    exchange_rate = models.DecimalField(
        max_digits=12, decimal_places=6, default=Decimal("1.000000")
    )
    method = models.CharField(
        max_length=20, choices=Method.choices, default=Method.BANK_TRANSFER
    )
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    bank_account = models.ForeignKey(
        "banking.BankAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments_received",
    )
    journal_entry = models.ForeignKey(
        "ledger.JournalEntry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payments"
        ordering = ["-date"]

    def __str__(self):
        return f"Payment {self.payment_number} - {self.amount} {self.currency}"


class CreditNote(models.Model):
    """Credit note issued against an invoice."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        APPLIED = "applied", "Applied"
        VOIDED = "voided", "Voided"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "accounts.Company", on_delete=models.CASCADE, related_name="credit_notes"
    )
    invoice = models.ForeignKey(
        Invoice, on_delete=models.PROTECT, related_name="credit_notes"
    )
    credit_note_number = models.CharField(max_length=30, unique=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    date = models.DateField()
    amount = models.DecimalField(
        max_digits=18, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    reason = models.TextField()
    journal_entry = models.ForeignKey(
        "ledger.JournalEntry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="credit_notes",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "credit_notes"
        ordering = ["-date"]

    def __str__(self):
        return f"CN {self.credit_note_number} - {self.amount}"


auditlog.register(Invoice)
auditlog.register(Payment)
auditlog.register(CreditNote)
