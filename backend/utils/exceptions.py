"""
Custom exception handling for LedgerPro API.
"""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class LedgerProException(APIException):
    """Base exception for LedgerPro-specific errors."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "A processing error occurred."
    default_code = "ledgerpro_error"


class DoubleEntryViolation(LedgerProException):
    """Raised when a double-entry accounting rule is violated."""

    default_detail = "Double-entry accounting rules were violated."
    default_code = "double_entry_violation"


class FiscalPeriodClosed(LedgerProException):
    """Raised when attempting to post to a closed fiscal period."""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "The target fiscal period is closed."
    default_code = "fiscal_period_closed"


class InsufficientPermissions(LedgerProException):
    """Raised when the user lacks the required role for an action."""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = "insufficient_permissions"


def custom_exception_handler(exc, context):
    """
    Custom exception handler that standardizes error response format
    and converts Django ValidationErrors into DRF ValidationErrors.
    """
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            exc = ValidationError(detail=exc.message_dict)
        else:
            exc = ValidationError(detail=exc.messages)

    response = exception_handler(exc, context)

    if response is not None:
        error_payload = {
            "status_code": response.status_code,
            "error": _get_error_type(response.status_code),
        }

        if isinstance(response.data, dict):
            error_payload["details"] = response.data
        elif isinstance(response.data, list):
            error_payload["details"] = {"non_field_errors": response.data}
        else:
            error_payload["details"] = {"message": str(response.data)}

        response.data = error_payload
    else:
        logger.exception(
            "Unhandled exception in %s",
            context.get("view", "unknown"),
            exc_info=exc,
        )

    return response


def _get_error_type(status_code: int) -> str:
    """Map HTTP status codes to human-readable error types."""
    mapping = {
        400: "Bad Request",
        401: "Authentication Required",
        403: "Permission Denied",
        404: "Not Found",
        405: "Method Not Allowed",
        409: "Conflict",
        422: "Unprocessable Entity",
        429: "Rate Limit Exceeded",
        500: "Internal Server Error",
    }
    return mapping.get(status_code, "Error")
