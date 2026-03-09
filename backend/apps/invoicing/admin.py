"""
Admin configuration for the invoicing app.
"""

from django.contrib import admin

from .models import CreditNote, Customer, Invoice, InvoiceLine, Payment


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 1
    readonly_fields = ("line_total", "tax_amount")
    fields = (
        "description", "quantity", "unit_price",
        "discount_percent", "tax_rate", "tax_amount",
        "line_total", "account", "order_index",
    )


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ("payment_number", "created_at")
    fields = (
        "payment_number", "date", "amount", "method",
        "reference", "created_at",
    )


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "name", "company", "email", "phone",
        "payment_terms", "credit_limit", "currency", "is_active",
    )
    list_filter = ("is_active", "currency", "company")
    search_fields = ("name", "email", "phone", "tax_id")
    readonly_fields = ("outstanding_balance", "created_at", "updated_at")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number", "customer", "status", "issue_date",
        "due_date", "total_amount", "balance_due", "currency",
    )
    list_filter = ("status", "company", "issue_date")
    search_fields = ("invoice_number", "customer__name")
    readonly_fields = (
        "invoice_number", "subtotal", "tax_amount",
        "total_amount", "amount_paid", "balance_due",
        "journal_entry", "created_at", "updated_at",
    )
    inlines = [InvoiceLineInline, PaymentInline]
    date_hierarchy = "issue_date"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "payment_number", "invoice", "date", "amount",
        "currency", "method", "created_by",
    )
    list_filter = ("method", "company", "date")
    search_fields = ("payment_number", "reference")
    readonly_fields = ("payment_number", "journal_entry", "created_at")
    date_hierarchy = "date"


@admin.register(CreditNote)
class CreditNoteAdmin(admin.ModelAdmin):
    list_display = (
        "credit_note_number", "invoice", "status",
        "date", "amount", "created_by",
    )
    list_filter = ("status", "company")
    search_fields = ("credit_note_number",)
    readonly_fields = (
        "credit_note_number", "journal_entry",
        "created_at", "updated_at",
    )
