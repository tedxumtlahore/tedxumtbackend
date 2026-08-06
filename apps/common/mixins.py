"""Reusable viewset mixins shared across the CMS apps."""


class ActiveQuerysetMixin:
    """Hide soft-deleted (is_active=False) rows from anonymous API consumers."""

    def get_queryset(self):
        queryset = super().get_queryset()
        request = getattr(self, 'request', None)
        user = getattr(request, 'user', None)
        if user is not None and user.is_staff:
            return queryset
        return queryset.filter(is_active=True)


class VisibleQuerysetMixin(ActiveQuerysetMixin):
    """Additionally hide rows the editors have unchecked as `is_visible`."""

    def get_queryset(self):
        queryset = super().get_queryset()
        request = getattr(self, 'request', None)
        user = getattr(request, 'user', None)
        if user is not None and user.is_staff:
            return queryset
        return queryset.filter(is_visible=True)


class SerializerContextMixin:
    """Guarantee `request` is in the serializer context so file URLs are absolute."""

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.setdefault('request', getattr(self, 'request', None))
        return context
