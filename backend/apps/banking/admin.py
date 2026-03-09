"""
Admin configuration for the banking app.
"""

from django.contrib import admin

from .models import BankAccount, BankTransaction, Reconciliation


class BankTransactionInline(admin.TabularInline):
    model = BankTransaction
    extra = 0
    readonly_fields = ("created_at",)
    fields = (
        "date", "description", "payee", "transaction_type",
        "amount", "status", "created_at",
    )


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = (
        "name", "bank_name", "masked_account_number", "account_type",
        "currency", "current_balance", "last_reconciled_date", "is_active",
    )
    list_filter = ("account_type", "currency", "is_active", "company")
    search_fields = ("name", "bank_name")
    readonly_fields = (
        "current_balance", "last_reconciled_date",
        "last_reconciled_balance", "created_at", "updated_at",
    )
    inlines = [BankTransactionInline]


@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "date", "bank_account", "description", "payee",
        "transaction_type", "amount", "status",
    )
    list_filter = ("transaction_type", "status", "bank_account")
    search_fields = ("description", "payee", "reference", "external_id")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "date"


@admin.register(Reconciliation)
class ReconciliationAdmin(admin.ModelAdmin):
    list_display = (
        "bank_account", "statement_date", "statement_balance",
        "cleared_balance", "difference", "status", "reconciled_by",
    )
    list_filter = ("status", "bank_account")
    readonly_fields = (
        "cleared_balance", "difference", "completed_at",
        "created_at", "updated_at",
    )
