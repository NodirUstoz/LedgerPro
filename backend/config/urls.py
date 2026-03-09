"""
URL configuration for LedgerPro.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Admin
    path("api/admin/", admin.site.urls),
    # API Schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # Authentication
    path("api/auth/", include("apps.accounts.urls")),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # App URLs
    path("api/ledger/", include("apps.ledger.urls")),
    path("api/invoicing/", include("apps.invoicing.urls")),
    path("api/expenses/", include("apps.expenses.urls")),
    path("api/banking/", include("apps.banking.urls")),
    path("api/reports/", include("apps.reports.urls")),
    path("api/tax/", include("apps.tax.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    try:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

# Admin site customization
admin.site.site_header = "LedgerPro Administration"
admin.site.site_title = "LedgerPro Admin"
admin.site.index_title = "Financial Management Dashboard"
