"""
Serializers for the tax app.
"""

from decimal import Decimal

from rest_framework import serializers

from .models import TaxExemption, TaxFiling, TaxRate


class TaxRateSerializer(serializers.ModelSerializer):
    """Serializer for TaxRate model."""

    tax_account_name = serializers.CharField(
        source="tax_account.name", read_only=True, default=None
    )

    class Meta:
        model = TaxRate
        fields = [
            "id", "company", "name", "code", "tax_type", "rate",
            "is_compound", "is_inclusive", "applies_to",
            "tax_account", "tax_account_name", "is_active",
            "effective_from", "effective_to", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_rate(self, value):
        if value < Decimal("0"):
            raise serializers.ValidationError("Tax rate cannot be negative.")
        if value > Decimal("100"):
            raise serializers.ValidationError("Tax rate cannot exceed 100%.")
        return value

    def validate(self, attrs):
        effective_from = attrs.get("effective_from")
        effective_to = attrs.get("effective_to")
        if effective_from and effective_to and effective_from >= effective_to:
            raise serializers.ValidationError(
                "Effective-from date must be before effective-to date."
            )
        return attrs


class TaxRateListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing tax rates."""

    class Meta:
        model = TaxRate
        fields = [
            "id", "name", "code", "tax_type", "rate",
            "applies_to", "is_active",
        ]


class TaxFilingSerializer(serializers.ModelSerializer):
    """Serializer for TaxFiling model."""

    prepared_by_name = serializers.CharField(
        source="prepared_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = TaxFiling
        fields = [
            "id", "company", "name", "tax_type", "frequency",
            "period_start", "period_end", "filing_deadline",
            "total_taxable_sales", "total_tax_collected",
            "total_taxable_purchases", "total_input_tax",
            "net_tax_liability", "adjustments", "total_due",
            "status", "filed_date", "confirmation_number",
            "notes", "journal_entry", "prepared_by", "prepared_by_name",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "net_tax_liability", "total_due",
            "journal_entry", "created_at", "updated_at",
        ]

    def validate(self, attrs):
        period_start = attrs.get("period_start")
        period_end = attrs.get("period_end")
        if period_start and period_end and period_start >= period_end:
            raise serializers.ValidationError(
                "Period start must be before period end."
            )
        return attrs


class TaxFilingListSerializer(serializers.ModelSerializer):
    """Lightweight list serializer for tax filings."""

    class Meta:
        model = TaxFiling
        fields = [
            "id", "name", "tax_type", "frequency",
            "period_start", "period_end", "filing_deadline",
            "total_due", "status", "filed_date",
        ]


class TaxExemptionSerializer(serializers.ModelSerializer):
    """Serializer for TaxExemption model."""

    customer_name = serializers.CharField(
        source="customer.name", read_only=True
    )
    is_valid = serializers.ReadOnlyField()

    class Meta:
        model = TaxExemption
        fields = [
            "id", "company", "customer", "customer_name",
            "certificate_number", "issuing_authority", "tax_type",
            "effective_from", "effective_to", "reason",
            "document", "is_active", "is_valid", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class TaxCalculationRequestSerializer(serializers.Serializer):
    """Serializer for tax calculation requests."""

    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    tax_rate_id = serializers.UUIDField()
    is_inclusive = serializers.BooleanField(default=False)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value
