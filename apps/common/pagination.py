"""Shared pagination classes."""

from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    """Standard pagination for list endpoints. Opt out with ?page_size=0 is not allowed."""

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class LargePagination(DefaultPagination):
    """For image-heavy listings such as the gallery."""

    page_size = 48
    max_page_size = 200
