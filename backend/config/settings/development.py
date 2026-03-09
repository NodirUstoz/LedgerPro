"""
Development settings for LedgerPro.
"""

from .base import *  # noqa: F401, F403

# =============================================================================
# Debug
# =============================================================================
DEBUG = True
ALLOWED_HOSTS = ["*"]

# =============================================================================
# Database (SQLite fallback for quick local dev)
# =============================================================================
import dj_database_url  # noqa: E402
import os  # noqa: E402

DATABASES = {
    "default": dj_database_url.config(
        default="postgresql://ledgerpro:ledgerpro_secret@localhost:5432/ledgerpro",
        conn_max_age=600,
    )
}

# =============================================================================
# Email
# =============================================================================
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# =============================================================================
# CORS - Allow all in development
# =============================================================================
CORS_ALLOW_ALL_ORIGINS = True

# =============================================================================
# Cache - Use local memory cache in development
# =============================================================================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "ledgerpro-dev-cache",
    }
}

# =============================================================================
# Static files
# =============================================================================
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# =============================================================================
# Logging
# =============================================================================
LOGGING["loggers"]["apps"]["level"] = "DEBUG"  # noqa: F405

# =============================================================================
# Django Debug Toolbar (if installed)
# =============================================================================
try:
    import debug_toolbar  # noqa: F401
    INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405
    INTERNAL_IPS = ["127.0.0.1"]
except ImportError:
    pass

# =============================================================================
# DRF - Browsable API in development
# =============================================================================
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]

# Disable throttling in development
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}  # noqa: F405

# Create logs directory
os.makedirs(BASE_DIR / "logs", exist_ok=True)  # noqa: F405
