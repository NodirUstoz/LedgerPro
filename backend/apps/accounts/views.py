"""
Views for accounts app.
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Company, CompanyMembership, FiscalYear
from .serializers import (
    ChangePasswordSerializer,
    CompanyMembershipSerializer,
    CompanySerializer,
    CustomTokenObtainPairSerializer,
    FiscalYearSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom login view returning JWT tokens and user info."""

    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    """User registration endpoint."""

    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "message": "Registration successful.",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ProfileView(generics.RetrieveUpdateAPIView):
    """View and update current user profile."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.UpdateAPIView):
    """Change password for authenticated user."""

    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Password updated successfully."},
            status=status.HTTP_200_OK,
        )


class CompanyViewSet(viewsets.ModelViewSet):
    """CRUD operations for companies."""

    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Company.objects.filter(
            memberships__user=self.request.user,
            memberships__is_active=True,
        ).distinct()

    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        """List all members of a company."""
        company = self.get_object()
        memberships = company.memberships.filter(is_active=True).select_related("user")
        serializer = CompanyMembershipSerializer(memberships, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def invite_member(self, request, pk=None):
        """Invite a user to the company."""
        company = self.get_object()
        membership = CompanyMembership.objects.filter(
            user=request.user, company=company, role__in=["admin", "manager"]
        ).first()
        if not membership:
            return Response(
                {"error": "You do not have permission to invite members."},
                status=status.HTTP_403_FORBIDDEN,
            )
        email = request.data.get("email")
        role = request.data.get("role", User.Role.VIEWER)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "User with this email not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        membership, created = CompanyMembership.objects.get_or_create(
            user=user,
            company=company,
            defaults={"role": role},
        )
        if not created:
            return Response(
                {"error": "User is already a member of this company."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            CompanyMembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def set_active(self, request, pk=None):
        """Set this company as the user's active company."""
        company = self.get_object()
        request.user.last_active_company = company
        request.user.save(update_fields=["last_active_company"])
        return Response({"message": f"Active company set to {company.name}."})


class FiscalYearViewSet(viewsets.ModelViewSet):
    """CRUD operations for fiscal years."""

    serializer_class = FiscalYearSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        company_id = self.request.query_params.get("company")
        qs = FiscalYear.objects.filter(
            company__memberships__user=self.request.user,
            company__memberships__is_active=True,
        )
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs.select_related("company")

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        """Close a fiscal year (prevents further posting)."""
        fiscal_year = self.get_object()
        if fiscal_year.is_closed:
            return Response(
                {"error": "Fiscal year is already closed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        fiscal_year.is_closed = True
        fiscal_year.closed_at = timezone.now()
        fiscal_year.closed_by = request.user
        fiscal_year.save()
        return Response(
            {"message": f"Fiscal year {fiscal_year.name} has been closed."}
        )

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        """Reopen a closed fiscal year (admin only)."""
        fiscal_year = self.get_object()
        membership = CompanyMembership.objects.filter(
            user=request.user,
            company=fiscal_year.company,
            role="admin",
        ).first()
        if not membership:
            return Response(
                {"error": "Only administrators can reopen fiscal years."},
                status=status.HTTP_403_FORBIDDEN,
            )
        fiscal_year.is_closed = False
        fiscal_year.closed_at = None
        fiscal_year.closed_by = None
        fiscal_year.save()
        return Response(
            {"message": f"Fiscal year {fiscal_year.name} has been reopened."}
        )
