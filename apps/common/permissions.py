"""Shared DRF permission classes."""

from rest_framework import permissions


class IsStaffOrReadOnly(permissions.BasePermission):
    """
    Public content is readable by anyone; only staff may write.

    The CMS is driven from the Django admin, so the API only ever needs
    anonymous reads plus authenticated staff writes.
    """

    message = 'Only staff members may modify this content.'

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class IsStaffOnly(permissions.BasePermission):
    """Staff-only access, including reads. Used for submitted applications."""

    message = 'Only staff members may access this resource.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)


class CreateOnlyOrStaff(permissions.BasePermission):
    """
    Anonymous visitors may POST (submit a form) but never read or edit.
    Staff may do everything.
    """

    message = 'Submissions are write-only for anonymous users.'

    def has_permission(self, request, view):
        if request.user and request.user.is_staff:
            return True
        return request.method == 'POST'
