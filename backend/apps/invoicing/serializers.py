"""
Serializers for invoicing app.
"""

from decimal import Decimal

from rest_framework import serializers

from .models import CreditNote, Customer, Invoice, InvoiceLine, Payment


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for Customer model."""

    outstanding_balance = serializers.ReadOnlyField()

    class Meta:
        model = Customer
        fields = [
            "id", "company", "name", "email", "phone", "tax_id",
            "billing_address", "shipping_address", "payment_terms",
            "credit_limit", "currency", "notes", "is_active",
            "outstanding_balance", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class InvoiceLineSerializer(serializers.ModelSerializer):
    """Serializer for individual invoice line items."""

    tax_rate_name = serializers.CharField(
        source="tax_rate.name", read_only=True, default=None
    )

    class Meta:
        model = InvoiceLine
        fields = [
            "id", "description", "quantity", "unit_price",
            "discount_percent", "tax_rate", "tax_rate_name",
            "tax_amount", "line_total", "account", "order_index",
        ]
        read_only_fields = ["id", "tax_amount", "line_total"]


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for Invoice with nested line items."""

    lines = InvoiceLineSerializer(many=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True
    )

    class Meta:
        model = Invoice
        fields = [
            "id", "company", "customer", "customer_name", "invoice_number",
            "status", "issue_date", "due_date", "currency", "exchange_rate",
            "subtotal", "tax_amount", "discount_amount", "total_amount",
            "amount_paid", "balance_due", "notes", "terms", "footer",
            "accounts_receivable", "revenue_account", "journal_entry",
            "created_by", "created_by_name", "lines",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "invoice_number", "subtotal", "tax_amount",
            "total_amount", "amount_paid", "balance_due",
            "journal_entry", "created_by", "created_at", "updated_at",
        ]

    def create(self, validated_data):
        lines_data = validated_data.pop("lines")
        user = self.context["request"].user
        validated_data["created_by"] = user

        # Generate invoice number
        last_inv = Invoice.objects.filter(
            company=validated_data["company"]
        ).order_by("-invoice_number").first()

        if last_inv:
            try:
                num = int(last_inv.invoice_number.replace("INV-", ""))
                validated_data["invoice_number"] = f"INV-{num + 1:06d}"
            except (ValueError, AttributeError):
                validated_data["invoice_number"] = "INV-000001"
        else:
            validated_data["invoice_number"] = "INV-000001"

        invoice = Invoice.objects.create(**validated_data)

        for idx, line_data in enumerate(lines_data):
            line_data["order_index"] = idx
            InvoiceLine.objects.create(invoice=invoice, **line_data)

        invoice.recalculate_totals()
        return invoice

    def update(self, instance, validated_data):
        if instance.status in [Invoice.Status.PAID, Invoice.Status.VOIDED]:
            raise serializers.ValidationError(
                "Cannot modify a paid or voided invoice."
            )

        lines_data = validated_data.pop("lines", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if lines_data is not None:
            instance.lines.all().delete()
            for idx, line_data in enumerate(lines_data):
                line_data["order_index"] = idx
                InvoiceLine.objects.create(invoice=instance, **line_data)
            instance.recalculate_totals()

        return instance


class InvoiceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing invoices."""

    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "invoice_number", "customer_name", "status",
            "issue_date", "due_date", "total_amount", "balance_due",
            "currency", "created_at",
        ]


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment model."""

    invoice_number = serializers.CharField(
        source="invoice.invoice_number", read_only=True
    )

    class Meta:
        model = Payment
        fields = [
            "id", "company", "invoice", "invoice_number", "payment_number",
            "date", "amount", "currency", "exchange_rate", "method",
            "reference", "notes", "bank_account", "journal_entry",
            "created_by", "created_at",
        ]
        read_only_fields = [
            "id", "payment_number", "journal_entry", "created_by", "created_at",
        ]

    def validate(self, attrs):
        invoice = attrs.get("invoice")
        amount = attrs.get("amount", Decimal("0.00"))

        if invoice and amount > invoice.balance_due:
            raise serializers.ValidationError(
                f"Payment amount ({amount}) exceeds invoice balance due ({invoice.balance_due})."
            )
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["created_by"] = user

        # Generate payment number
        last_pmt = Payment.objects.filter(
            company=validated_data["company"]
        ).order_by("-payment_number").first()

        if last_pmt:
            try:
                num = int(last_pmt.payment_number.replace("PMT-", ""))
                validated_data["payment_number"] = f"PMT-{num + 1:06d}"
            except (ValueError, AttributeError):
                validated_data["payment_number"] = "PMT-000001"
        else:
            validated_data["payment_number"] = "PMT-000001"

        payment = Payment.objects.create(**validated_data)

        # Update invoice
        invoice = payment.invoice
        invoice.amount_paid += payment.amount
        invoice.update_payment_status()

        return payment


class CreditNoteSerializer(serializers.ModelSerializer):
    """Serializer for CreditNote model."""

    invoice_number = serializers.CharField(
        source="invoice.invoice_number", read_only=True
    )

    class Meta:
        model = CreditNote
        fields = [
            "id", "company", "invoice", "invoice_number",
            "credit_note_number", "status", "date", "amount",
            "reason", "journal_entry", "created_by", "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "credit_note_number", "journal_entry",
            "created_by", "created_at", "updated_at",
        ]

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["created_by"] = user

        last_cn = CreditNote.objects.filter(
            company=validated_data["company"]
        ).order_by("-credit_note_number").first()

        if last_cn:
            try:
                num = int(last_cn.credit_note_number.replace("CN-", ""))
                validated_data["credit_note_number"] = f"CN-{num + 1:06d}"
            except (ValueError, AttributeError):
                validated_data["credit_note_number"] = "CN-000001"
        else:
            validated_data["credit_note_number"] = "CN-000001"

        return CreditNote.objects.create(**validated_data)
