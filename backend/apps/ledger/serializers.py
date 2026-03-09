"""
Serializers for ledger app.
"""

from decimal import Decimal

from rest_framework import serializers

from .models import Account, AccountSubType, AccountType, ExchangeRate, JournalEntry, JournalLine


class AccountSerializer(serializers.ModelSerializer):
    """Serializer for Account (Chart of Accounts) model."""

    full_path = serializers.ReadOnlyField()
    parent_name = serializers.CharField(source="parent.name", read_only=True, default=None)
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            "id", "company", "code", "name", "description", "account_type",
            "sub_type", "normal_balance", "parent", "parent_name", "currency",
            "is_active", "is_system", "tax_rate", "opening_balance",
            "current_balance", "full_path", "children_count",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "current_balance", "is_system", "created_at", "updated_at",
        ]

    def get_children_count(self, obj):
        return obj.children.count()

    def validate_code(self, value):
        company = self.context.get("company") or self.initial_data.get("company")
        qs = Account.objects.filter(company_id=company, code=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                f"Account code '{value}' already exists for this company."
            )
        return value


class AccountTreeSerializer(serializers.ModelSerializer):
    """Recursive serializer for hierarchical account tree display."""

    children = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            "id", "code", "name", "account_type", "sub_type",
            "normal_balance", "current_balance", "is_active", "children",
        ]

    def get_children(self, obj):
        children = obj.children.filter(is_active=True).order_by("code")
        return AccountTreeSerializer(children, many=True).data


class JournalLineSerializer(serializers.ModelSerializer):
    """Serializer for individual journal lines."""

    account_code = serializers.CharField(source="account.code", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = JournalLine
        fields = [
            "id", "account", "account_code", "account_name", "description",
            "debit_amount", "credit_amount", "currency", "exchange_rate",
            "base_debit_amount", "base_credit_amount", "tax_rate",
            "tax_amount", "reconciled", "created_at",
        ]
        read_only_fields = [
            "id", "base_debit_amount", "base_credit_amount", "created_at",
        ]

    def validate(self, attrs):
        debit = attrs.get("debit_amount", Decimal("0.00"))
        credit = attrs.get("credit_amount", Decimal("0.00"))

        if debit < 0 or credit < 0:
            raise serializers.ValidationError("Amounts cannot be negative.")

        if debit > 0 and credit > 0:
            raise serializers.ValidationError(
                "A line cannot have both debit and credit amounts."
            )

        if debit == 0 and credit == 0:
            raise serializers.ValidationError(
                "A line must have either a debit or credit amount."
            )

        return attrs


class JournalEntrySerializer(serializers.ModelSerializer):
    """Serializer for journal entries with nested lines."""

    lines = JournalLineSerializer(many=True)
    total_debit = serializers.ReadOnlyField()
    total_credit = serializers.ReadOnlyField()
    is_balanced = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True
    )
    approved_by_name = serializers.CharField(
        source="approved_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = JournalEntry
        fields = [
            "id", "company", "entry_number", "date", "description",
            "reference", "entry_type", "status", "fiscal_year",
            "currency", "exchange_rate", "source_module", "source_id",
            "reversing_entry", "created_by", "created_by_name",
            "approved_by", "approved_by_name", "posted_at",
            "total_debit", "total_credit", "is_balanced",
            "lines", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "entry_number", "status", "created_by",
            "approved_by", "posted_at", "created_at", "updated_at",
        ]

    def create(self, validated_data):
        lines_data = validated_data.pop("lines")
        from .services import create_journal_entry

        formatted_lines = []
        for line in lines_data:
            formatted_lines.append({
                "account_id": str(line["account"].id),
                "debit_amount": str(line.get("debit_amount", "0.00")),
                "credit_amount": str(line.get("credit_amount", "0.00")),
                "description": line.get("description", ""),
                "tax_rate_id": str(line["tax_rate"].id) if line.get("tax_rate") else None,
                "tax_amount": str(line.get("tax_amount", "0.00")),
            })

        return create_journal_entry(
            company=validated_data["company"],
            entry_date=validated_data["date"],
            description=validated_data["description"],
            lines_data=formatted_lines,
            created_by=self.context["request"].user,
            entry_type=validated_data.get("entry_type", JournalEntry.EntryType.STANDARD),
            reference=validated_data.get("reference", ""),
            currency=validated_data.get("currency", "USD"),
            exchange_rate=validated_data.get("exchange_rate", Decimal("1.000000")),
        )

    def update(self, instance, validated_data):
        if instance.status == JournalEntry.Status.POSTED:
            raise serializers.ValidationError(
                "Posted entries cannot be modified. Void or reverse instead."
            )
        lines_data = validated_data.pop("lines", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if lines_data is not None:
            instance.lines.all().delete()
            for line_data in lines_data:
                JournalLine.objects.create(
                    journal_entry=instance,
                    account=line_data["account"],
                    description=line_data.get("description", ""),
                    debit_amount=line_data.get("debit_amount", Decimal("0.00")),
                    credit_amount=line_data.get("credit_amount", Decimal("0.00")),
                    currency=instance.currency,
                    exchange_rate=instance.exchange_rate,
                )

        return instance


class JournalEntryListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing journal entries."""

    total_debit = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True
    )
    line_count = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntry
        fields = [
            "id", "entry_number", "date", "description", "reference",
            "entry_type", "status", "total_debit", "currency",
            "created_by_name", "line_count", "posted_at", "created_at",
        ]

    def get_line_count(self, obj):
        return obj.lines.count()


class ExchangeRateSerializer(serializers.ModelSerializer):
    """Serializer for exchange rates."""

    class Meta:
        model = ExchangeRate
        fields = [
            "id", "base_currency", "target_currency", "rate",
            "date", "source", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class TrialBalanceRequestSerializer(serializers.Serializer):
    """Serializer for trial balance request parameters."""

    company_id = serializers.UUIDField()
    as_of_date = serializers.DateField()
