"""
Pagination utilities for LedgerPro API.
"""

from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination with configurable page size."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200

    def get_paginated_response(self, data):
        from rest_framework.response import Response

        return Response({
            "count": self.page.paginator.count,
            "total_pages": self.page.paginator.num_pages,
            "current_page": self.page.number,
            "page_size": self.get_page_size(self.request),
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        })


class LargeResultsSetPagination(PageNumberPagination):
    """Pagination for large result sets (e.g., transaction lists)."""

    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 500
