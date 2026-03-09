"""
Admin configuration for the expenses app.
"""

from django.contrib import admin

from .models import Expense, ExpenseCategory, Receipt, Vendor


class ReceiptInline(admin.TabularInline):
    model = Receipt
    extra = 0
    readonly_fields = ("uploaded_at", "file_size", "mime_type")


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name", "company", "parent", "default_account",
        "budget_amount", "is_active",
    )
    list_filter = ("is_active", "company")
    search_fields = ("name", "description")
    readonly_fields = ("created_at",)


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = (
        "name", "company", "email", "phone", "payment_terms",
        "currency", "is_active",
    )
    list_filter = ("is_active", "currency", "company")
    search_fields = ("name", "email", "tax_id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = (
        "expense_number", "vendor", "category", "date",
        "total_amount", "currency", "status", "created_by",
    )
    list_filter = ("status", "category", "company", "date")
    search_fields = ("expense_number", "description", "vendor__name")
    readonly_fields = (
        "expense_number", "total_amount", "journal_entry",
        "created_at", "updated_at",
    )
    inlines = [ReceiptInline]
    date_hierarchy = "date"


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = (
        "filename", "expense", "file_size", "mime_type",
        "uploaded_by", "uploaded_at",
    )
    search_fields = ("filename",)
    readonly_fields = ("uploaded_at",)
