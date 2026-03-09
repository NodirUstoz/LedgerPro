"""
Serializers for accounts app.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Company, CompanyMembership, FiscalYear

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer that includes user info in the response."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["name"] = user.full_name
        token["role"] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class UserSerializer(serializers.ModelSerializer):
    """Serializer for the User model."""

    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name",
            "phone", "role", "avatar", "timezone", "date_format",
            "is_email_verified", "last_active_company", "created_at",
        ]
        read_only_fields = ["id", "email", "is_email_verified", "created_at"]


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            "email", "first_name", "last_name", "password", "password_confirm",
            "phone", "timezone",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(**validated_data)
        return user


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "New passwords do not match."}
            )
        return attrs

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user


class CompanySerializer(serializers.ModelSerializer):
    """Serializer for the Company model."""

    owner_name = serializers.CharField(source="owner.full_name", read_only=True)
    current_fiscal_year = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            "id", "name", "legal_name", "tax_id", "industry", "website",
            "email", "phone", "address_line1", "address_line2", "city",
            "state", "postal_code", "country", "base_currency", "logo",
            "owner", "owner_name", "is_active", "current_fiscal_year",
            "member_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "owner", "created_at", "updated_at"]

    def get_current_fiscal_year(self, obj):
        fy = obj.current_fiscal_year
        if fy:
            return FiscalYearSerializer(fy).data
        return None

    def get_member_count(self, obj):
        return obj.memberships.filter(is_active=True).count()

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["owner"] = user
        company = super().create(validated_data)
        CompanyMembership.objects.create(
            user=user, company=company, role=User.Role.ADMIN
        )
        return company


class CompanyMembershipSerializer(serializers.ModelSerializer):
    """Serializer for company memberships."""

    user_email = serializers.CharField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = CompanyMembership
        fields = [
            "id", "user", "user_email", "user_name", "company",
            "company_name", "role", "is_active", "joined_at",
        ]
        read_only_fields = ["id", "joined_at"]


class FiscalYearSerializer(serializers.ModelSerializer):
    """Serializer for the FiscalYear model."""

    class Meta:
        model = FiscalYear
        fields = [
            "id", "company", "name", "start_date", "end_date",
            "is_closed", "closed_at", "closed_by", "created_at",
        ]
        read_only_fields = ["id", "closed_at", "closed_by", "created_at"]

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError("Start date must be before end date.")
        company = attrs.get("company")
        if company:
            overlapping = FiscalYear.objects.filter(
                company=company,
                start_date__lt=end_date,
                end_date__gt=start_date,
            )
            if self.instance:
                overlapping = overlapping.exclude(pk=self.instance.pk)
            if overlapping.exists():
                raise serializers.ValidationError(
                    "Fiscal year dates overlap with an existing fiscal year."
                )
        return attrs
