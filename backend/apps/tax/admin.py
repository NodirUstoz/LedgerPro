"""
Admin configuration for the tax app.
"""

from django.contrib import admin

from .models import TaxExemption, TaxFiling, TaxRate


@admin.register(TaxRate)
class TaxRateAdmin(admin.ModelAdmin):
    list_display = (
        "name", "code", "tax_type", "rate", "applies_to",
        "is_compound", "is_inclusive", "is_active",
    )
    list_filter = ("tax_type", "applies_to", "is_active", "is_compound", "company")
    search_fields = ("name", "code")
    list_editable = ("is_active",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {
            "fields": ("company", "name", "code", "tax_type", "rate"),
        }),
        ("Behavior", {
            "fields": ("is_compound", "is_inclusive", "applies_to"),
        }),
        ("Accounting", {
            "fields": ("tax_account",),
        }),
        ("Validity", {
            "fields": ("is_active", "effective_from", "effective_to"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


@admin.register(TaxFiling)
class TaxFilingAdmin(admin.ModelAdmin):
    list_display = (
        "name", "company", "tax_type", "frequency",
        "period_start", "period_end", "filing_deadline",
        "total_due", "status", "filed_date",
    )
    list_filter = ("status", "tax_type", "frequency", "company")
    search_fields = ("name", "confirmation_number")
    readonly_fields = (
        "net_tax_liability", "total_due",
        "created_at", "updated_at",
    )
    date_hierarchy = "period_end"


@admin.register(TaxExemption)
class TaxExemptionAdmin(admin.ModelAdmin):
    list_display = (
        "certificate_number", "customer", "tax_type",
        "effective_from", "effective_to", "is_active",
    )
    list_filter = ("tax_type", "is_active", "company")
    search_fields = ("certificate_number", "customer__name", "issuing_authority")
    readonly_fields = ("created_at",)
