"""
Tax rate, tax filing, and tax calculation models for LedgerPro.
"""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from auditlog.registry import auditlog


class TaxRate(models.Model):
    """Tax rate definition used across invoices, expenses, and journal entries."""

    class TaxType(models.TextChoices):
        SALES_TAX = "sales_tax", "Sales Tax"
        VAT = "vat", "Value Added Tax"
        GST = "gst", "Goods & Services Tax"
        WITHHOLDING = "withholding", "Withholding Tax"
        INCOME_TAX = "income_tax", "Income Tax"
        EXCISE = "excise", "Excise Tax"
        CUSTOM = "custom", "Custom"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "accounts.Company", on_delete=models.CASCADE, related_name="tax_rates"
    )
    name = models.CharField(max_length=100, help_text="e.g., CA Sales Tax 8.25%")
    code = models.CharField(max_length=20, help_text="Short code like VAT-20, ST-8.25")
    tax_type = models.CharField(
        max_length=20, choices=TaxType.choices, default=TaxType.SALES_TAX
    )
    rate = models.DecimalField(
        max_digits=8, decimal_places=4,
        help_text="Tax rate as a percentage, e.g. 8.2500 for 8.25%.",
    )
    is_compound = models.BooleanField(
        default=False,
        help_text="If True, this tax is calculated on top of other taxes.",
    )
    is_inclusive = models.BooleanField(
        default=False,
        help_text="If True, tax is included in the item price.",
    )
    applies_to = models.CharField(
        max_length=20,
        choices=[("sales", "Sales"), ("purchases", "Purchases"), ("both", "Both")],
        default="both",
    )
    tax_account = models.ForeignKey(
        "ledger.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="tax_rates_collected",
        help_text="Liability account where collected tax is posted.",
    )
    is_active = models.BooleanField(default=True)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tax_rates"
        ordering = ["name"]
        unique_together = ("company", "code")

    def __str__(self):
        return f"{self.name} ({self.rate}%)"

    def calculate_tax(self, amount: Decimal) -> Decimal:
        """Calculate tax on a given amount."""
        if self.is_inclusive:
            return amount - (amount / (1 + self.rate / Decimal("100")))
        return amount * self.rate / Decimal("100")


class TaxFiling(models.Model):
    """Represents a tax filing period and its calculated amounts."""

    class FilingStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        CALCULATED = "calculated", "Calculated"
        FILED = "filed", "Filed"
        AMENDED = "amended", "Amended"

    class FilingFrequency(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        ANNUALLY = "annually", "Annually"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "accounts.Company", on_delete=models.CASCADE, related_name="tax_filings"
    )
    name = models.CharField(max_length=100, help_text="e.g., Q1 2025 Sales Tax")
    tax_type = models.CharField(
        max_length=20,
        choices=TaxRate.TaxType.choices,
        default=TaxRate.TaxType.SALES_TAX,
    )
    frequency = models.CharField(
        max_length=20,
        choices=FilingFrequency.choices,
        default=FilingFrequency.QUARTERLY,
    )
    period_start = models.DateField()
    period_end = models.DateField()
    filing_deadline = models.DateField()

    # Calculated amounts
    total_taxable_sales = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    total_tax_collected = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    total_taxable_purchases = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    total_input_tax = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    net_tax_liability = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00"),
        help_text="Tax collected minus input tax credits.",
    )
    adjustments = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )
    total_due = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0.00")
    )

    status = models.CharField(
        max_length=20,
        choices=FilingStatus.choices,
        default=FilingStatus.DRAFT,
    )
    filed_date = models.DateField(null=True, blank=True)
    confirmation_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    journal_entry = models.ForeignKey(
        "ledger.JournalEntry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tax_filings",
    )
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="prepared_tax_filings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tax_filings"
        ordering = ["-period_end"]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    def calculate_liability(self):
        """Calculate net tax liability from collected and input taxes."""
        self.net_tax_liability = self.total_tax_collected - self.total_input_tax
        self.total_due = self.net_tax_liability + self.adjustments
        self.status = self.FilingStatus.CALCULATED
        self.save(update_fields=[
            "net_tax_liability", "total_due", "status",
        ])


class TaxExemption(models.Model):
    """Tax exemption certificates for customers or products."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "accounts.Company", on_delete=models.CASCADE, related_name="tax_exemptions"
    )
    customer = models.ForeignKey(
        "invoicing.Customer",
        on_delete=models.CASCADE,
        related_name="tax_exemptions",
    )
    certificate_number = models.CharField(max_length=100)
    issuing_authority = models.CharField(max_length=255)
    tax_type = models.CharField(
        max_length=20, choices=TaxRate.TaxType.choices
    )
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    reason = models.TextField(blank=True)
    document = models.FileField(
        upload_to="tax_exemptions/", blank=True, null=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tax_exemptions"
        ordering = ["-effective_from"]

    def __str__(self):
        return f"Exemption {self.certificate_number} - {self.customer.name}"

    @property
    def is_valid(self):
        """Check if exemption is currently valid."""
        from datetime import date
        today = date.today()
        if not self.is_active:
            return False
        if today < self.effective_from:
            return False
        if self.effective_to and today > self.effective_to:
            return False
        return True


auditlog.register(TaxRate)
auditlog.register(TaxFiling)
auditlog.register(TaxExemption)
