"""
Serializers for expenses app.
"""

from rest_framework import serializers

from .models import Expense, ExpenseCategory, Receipt, Vendor


class ExpenseCategorySerializer(serializers.ModelSerializer):
    """Serializer for ExpenseCategory model."""

    subcategories = serializers.SerializerMethodField()
    spent_this_month = serializers.SerializerMethodField()

    class Meta:
        model = ExpenseCategory
        fields = [
            "id", "company", "name", "description", "parent",
            "default_account", "budget_amount", "is_active",
            "subcategories", "spent_this_month", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_subcategories(self, obj):
        children = obj.subcategories.filter(is_active=True)
        return ExpenseCategorySerializer(children, many=True).data

    def get_spent_this_month(self, obj):
        from datetime import date
        from django.db.models import Sum

        today = date.today()
        total = obj.expenses.filter(
            date__year=today.year,
            date__month=today.month,
            status__in=["approved", "paid"],
        ).aggregate(total=Sum("total_amount"))["total"]
        return str(total or "0.00")


class VendorSerializer(serializers.ModelSerializer):
    """Serializer for Vendor model."""

    class Meta:
        model = Vendor
        fields = [
            "id", "company", "name", "email", "phone", "tax_id",
            "address", "payment_terms", "currency", "default_category",
            "notes", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ReceiptSerializer(serializers.ModelSerializer):
    """Serializer for Receipt model."""

    class Meta:
        model = Receipt
        fields = [
            "id", "expense", "file", "filename", "file_size",
            "mime_type", "uploaded_by", "uploaded_at",
        ]
        read_only_fields = ["id", "filename", "file_size", "mime_type", "uploaded_by", "uploaded_at"]


class ExpenseSerializer(serializers.ModelSerializer):
    """Serializer for Expense model."""

    receipts = ReceiptSerializer(many=True, read_only=True)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True, default=None)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)

    class Meta:
        model = Expense
        fields = [
            "id", "company", "expense_number", "vendor", "vendor_name",
            "category", "category_name", "date", "due_date", "description",
            "amount", "tax_amount", "total_amount", "currency", "exchange_rate",
            "status", "payment_method", "reference", "notes", "is_billable",
            "billable_customer", "expense_account", "payment_account",
            "journal_entry", "tax_rate", "created_by", "created_by_name",
            "approved_by", "receipts", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "expense_number", "total_amount", "journal_entry",
            "created_by", "approved_by", "created_at", "updated_at",
        ]

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["created_by"] = user

        # Generate expense number
        last_exp = Expense.objects.filter(
            company=validated_data["company"]
        ).order_by("-expense_number").first()

        if last_exp:
            try:
                num = int(last_exp.expense_number.replace("EXP-", ""))
                validated_data["expense_number"] = f"EXP-{num + 1:06d}"
            except (ValueError, AttributeError):
                validated_data["expense_number"] = "EXP-000001"
        else:
            validated_data["expense_number"] = "EXP-000001"

        return Expense.objects.create(**validated_data)


class ExpenseListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing expenses."""

    vendor_name = serializers.CharField(source="vendor.name", read_only=True, default=None)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)

    class Meta:
        model = Expense
        fields = [
            "id", "expense_number", "vendor_name", "category_name",
            "date", "description", "total_amount", "currency",
            "status", "created_at",
        ]
