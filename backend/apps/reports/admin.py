"""
Admin configuration for the reports app.
"""

from django.contrib import admin

from .models import ReportSchedule, SavedReport


@admin.register(SavedReport)
class SavedReportAdmin(admin.ModelAdmin):
    list_display = (
        "name", "company", "report_type", "period_start",
        "period_end", "file_format", "generated_by",
        "is_favorite", "created_at",
    )
    list_filter = ("report_type", "file_format", "is_favorite", "company")
    search_fields = ("name",)
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "name", "company", "report_type", "frequency",
        "file_format", "is_active", "last_generated",
    )
    list_filter = ("report_type", "frequency", "is_active", "company")
    search_fields = ("name",)
    readonly_fields = ("last_generated", "created_at", "updated_at")
