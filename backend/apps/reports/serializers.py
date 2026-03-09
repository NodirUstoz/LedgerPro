"""
Serializers for the reports app.
"""

from rest_framework import serializers

from .models import ReportSchedule, SavedReport


class SavedReportSerializer(serializers.ModelSerializer):
    """Serializer for SavedReport model."""

    generated_by_name = serializers.CharField(
        source="generated_by.full_name", read_only=True, default=None
    )
    report_type_display = serializers.CharField(
        source="get_report_type_display", read_only=True
    )

    class Meta:
        model = SavedReport
        fields = [
            "id", "company", "name", "report_type", "report_type_display",
            "parameters", "data", "file", "file_format",
            "period_start", "period_end", "generated_by",
            "generated_by_name", "is_favorite", "created_at",
        ]
        read_only_fields = ["id", "generated_by", "created_at"]


class SavedReportListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing saved reports."""

    report_type_display = serializers.CharField(
        source="get_report_type_display", read_only=True
    )

    class Meta:
        model = SavedReport
        fields = [
            "id", "name", "report_type", "report_type_display",
            "period_start", "period_end", "file_format",
            "is_favorite", "created_at",
        ]


class ReportScheduleSerializer(serializers.ModelSerializer):
    """Serializer for ReportSchedule model."""

    class Meta:
        model = ReportSchedule
        fields = [
            "id", "company", "report_type", "name", "frequency",
            "parameters", "recipients", "file_format",
            "is_active", "last_generated", "created_by",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "last_generated", "created_by", "created_at", "updated_at"]


class IncomeStatementRequestSerializer(serializers.Serializer):
    """Parameters for generating an income statement."""

    company_id = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    compare_prior_period = serializers.BooleanField(default=False)

    def validate(self, attrs):
        if attrs["start_date"] >= attrs["end_date"]:
            raise serializers.ValidationError(
                "Start date must be before end date."
            )
        return attrs


class BalanceSheetRequestSerializer(serializers.Serializer):
    """Parameters for generating a balance sheet."""

    company_id = serializers.UUIDField()
    as_of_date = serializers.DateField()
    compare_prior_period = serializers.BooleanField(default=False)


class CashFlowRequestSerializer(serializers.Serializer):
    """Parameters for generating a cash flow statement."""

    company_id = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, attrs):
        if attrs["start_date"] >= attrs["end_date"]:
            raise serializers.ValidationError(
                "Start date must be before end date."
            )
        return attrs
