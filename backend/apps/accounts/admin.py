"""
Admin configuration for accounts app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Company, CompanyMembership, FiscalYear, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "first_name", "last_name", "role", "is_active", "created_at")
    list_filter = ("role", "is_active", "is_staff", "is_email_verified")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "phone", "avatar")}),
        ("Role & Preferences", {"fields": ("role", "timezone", "date_format", "last_active_company")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "is_email_verified", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "created_at")}),
    )
    readonly_fields = ("created_at",)
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "password1", "password2", "role"),
        }),
    )


class CompanyMembershipInline(admin.TabularInline):
    model = CompanyMembership
    extra = 0
    readonly_fields = ("joined_at",)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "industry", "base_currency", "is_active", "created_at")
    list_filter = ("industry", "is_active", "base_currency")
    search_fields = ("name", "legal_name", "tax_id")
    inlines = [CompanyMembershipInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(FiscalYear)
class FiscalYearAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "start_date", "end_date", "is_closed")
    list_filter = ("is_closed", "company")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at", "closed_at", "closed_by")
