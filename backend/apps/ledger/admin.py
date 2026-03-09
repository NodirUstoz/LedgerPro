"""
Admin configuration for ledger app.
"""

from django.contrib import admin

from .models import Account, ExchangeRate, JournalEntry, JournalLine


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 2
    readonly_fields = ("base_debit_amount", "base_credit_amount", "created_at")
    autocomplete_fields = ("account",)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        "code", "name", "account_type", "sub_type", "normal_balance",
        "current_balance", "currency", "is_active",
    )
    list_filter = ("account_type", "sub_type", "is_active", "company")
    search_fields = ("code", "name", "description")
    list_editable = ("is_active",)
    readonly_fields = ("current_balance", "created_at", "updated_at")
    ordering = ("code",)


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = (
        "entry_number", "date", "description", "entry_type", "status",
        "total_debit", "currency", "created_by", "posted_at",
    )
    list_filter = ("status", "entry_type", "company", "date")
    search_fields = ("entry_number", "description", "reference")
    readonly_fields = (
        "entry_number", "total_debit", "total_credit", "is_balanced",
        "posted_at", "created_at", "updated_at",
    )
    inlines = [JournalLineInline]
    date_hierarchy = "date"


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ("base_currency", "target_currency", "rate", "date", "source")
    list_filter = ("base_currency", "target_currency")
    date_hierarchy = "date"
