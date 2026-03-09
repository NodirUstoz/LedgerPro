"""
User, Company, and FiscalYear models for LedgerPro.
"""

import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models
from auditlog.registry import auditlog


class UserManager(BaseUserManager):
    """Custom user manager supporting email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email address is required.")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model using email as the primary identifier."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        MANAGER = "manager", "Manager"
        ACCOUNTANT = "accountant", "Accountant"
        AUDITOR = "auditor", "Auditor"
        VIEWER = "viewer", "Viewer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    email = models.EmailField("email address", unique=True, db_index=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(r"^\+?1?\d{9,15}$", "Enter a valid phone number.")],
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    timezone = models.CharField(max_length=50, default="UTC")
    date_format = models.CharField(max_length=20, default="%Y-%m-%d")
    is_email_verified = models.BooleanField(default=False)
    last_active_company = models.ForeignKey(
        "Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="last_active_users",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def has_company_access(self, company):
        """Check if user has access to the given company."""
        return self.company_memberships.filter(company=company, is_active=True).exists()


class Company(models.Model):
    """Company / Organization entity for multi-tenant support."""

    class Industry(models.TextChoices):
        TECHNOLOGY = "technology", "Technology"
        FINANCE = "finance", "Finance"
        HEALTHCARE = "healthcare", "Healthcare"
        MANUFACTURING = "manufacturing", "Manufacturing"
        RETAIL = "retail", "Retail"
        SERVICES = "services", "Services"
        CONSTRUCTION = "construction", "Construction"
        EDUCATION = "education", "Education"
        NONPROFIT = "nonprofit", "Non-Profit"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    legal_name = models.CharField(max_length=255, blank=True)
    tax_id = models.CharField(max_length=50, blank=True, help_text="EIN, VAT number, etc.")
    industry = models.CharField(max_length=50, choices=Industry.choices, default=Industry.OTHER)
    website = models.URLField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=2, default="US", help_text="ISO 3166-1 alpha-2")
    base_currency = models.CharField(max_length=3, default="USD")
    logo = models.ImageField(upload_to="company_logos/", blank=True, null=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_companies",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "companies"
        ordering = ["name"]
        verbose_name = "company"
        verbose_name_plural = "companies"

    def __str__(self):
        return self.name

    @property
    def current_fiscal_year(self):
        """Return the active fiscal year."""
        return self.fiscal_years.filter(is_closed=False).order_by("-start_date").first()


class CompanyMembership(models.Model):
    """Associates users with companies and defines their role within each."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="company_memberships",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=User.Role.choices,
        default=User.Role.VIEWER,
    )
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "company_memberships"
        unique_together = ("user", "company")
        verbose_name = "company membership"

    def __str__(self):
        return f"{self.user.email} - {self.company.name} ({self.role})"


class FiscalYear(models.Model):
    """Fiscal year definition for a company."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="fiscal_years",
    )
    name = models.CharField(max_length=100, help_text="e.g., FY 2025")
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(
        default=False,
        help_text="Once closed, no new entries can be posted to this period.",
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_fiscal_years",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "fiscal_years"
        ordering = ["-start_date"]
        unique_together = ("company", "name")
        verbose_name = "fiscal year"
        verbose_name_plural = "fiscal years"

    def __str__(self):
        return f"{self.company.name} - {self.name}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError("Start date must be before end date.")
        overlapping = FiscalYear.objects.filter(
            company=self.company,
            start_date__lt=self.end_date,
            end_date__gt=self.start_date,
        ).exclude(pk=self.pk)
        if overlapping.exists():
            raise ValidationError("Fiscal year dates overlap with an existing fiscal year.")


# Register models with audit log
auditlog.register(User, exclude_fields=["password", "last_login"])
auditlog.register(Company)
auditlog.register(FiscalYear)
