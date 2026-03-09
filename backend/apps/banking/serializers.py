"""
Serializers for banking app.
"""

from rest_framework import serializers

from .models import BankAccount, BankTransaction, Reconciliation


class BankAccountSerializer(serializers.ModelSerializer):
    """Serializer for BankAccount model."""

    masked_account_number = serializers.ReadOnlyField()
    ledger_account_name = serializers.CharField(
        source="ledger_account.name", read_only=True, default=None
    )
    transaction_count = serializers.SerializerMethodField()

    class Meta:
        model = BankAccount
        fields = [
            "id", "company", "name", "bank_name", "account_number",
            "masked_account_number", "routing_number", "account_type",
            "currency", "current_balance", "last_reconciled_date",
            "last_reconciled_balance", "ledger_account", "ledger_account_name",
            "is_active", "transaction_count", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "current_balance", "last_reconciled_date",
            "last_reconciled_balance", "created_at", "updated_at",
        ]

    def get_transaction_count(self, obj):
        return obj.transactions.count()


class BankTransactionSerializer(serializers.ModelSerializer):
    """Serializer for BankTransaction model."""

    bank_account_name = serializers.CharField(
        source="bank_account.name", read_only=True
    )

    class Meta:
        model = BankTransaction
        fields = [
            "id", "bank_account", "bank_account_name", "date", "description",
            "reference", "transaction_type", "amount", "running_balance",
            "status", "payee", "category", "journal_entry",
            "matched_journal_line", "external_id", "import_batch",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "import_batch", "created_at", "updated_at"]


class BankTransactionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing bank transactions."""

    class Meta:
        model = BankTransaction
        fields = [
            "id", "date", "description", "payee", "transaction_type",
            "amount", "running_balance", "status", "created_at",
        ]


class ReconciliationSerializer(serializers.ModelSerializer):
    """Serializer for Reconciliation model."""

    bank_account_name = serializers.CharField(
        source="bank_account.name", read_only=True
    )
    transaction_ids = serializers.PrimaryKeyRelatedField(
        source="transactions",
        many=True,
        queryset=BankTransaction.objects.all(),
        required=False,
    )

    class Meta:
        model = Reconciliation
        fields = [
            "id", "bank_account", "bank_account_name", "statement_date",
            "statement_balance", "opening_balance", "cleared_balance",
            "difference", "status", "transaction_ids", "notes",
            "reconciled_by", "completed_at", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "cleared_balance", "difference", "reconciled_by",
            "completed_at", "created_at", "updated_at",
        ]
