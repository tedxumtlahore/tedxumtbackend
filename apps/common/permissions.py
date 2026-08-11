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


#: Group names created by apps/ticketing/migrations (see 0002_roles).
VOLUNTEERS_GROUP = 'Volunteers'
ORGANIZERS_GROUP = 'Organizers'


def in_group(user, name):
    """True if `user` is staff (staff can do anything) or in the named group."""
    if not (user and user.is_authenticated):
        return False
    if user.is_staff:
        return True
    return user.groups.filter(name=name).exists()


class IsVolunteer(permissions.BasePermission):
    """Check-in portal access: the Volunteers group, or any staff member."""

    message = 'You need volunteer access to use the check-in portal.'

    def has_permission(self, request, view):
        return in_group(request.user, VOLUNTEERS_GROUP)


class IsOrganizer(permissions.BasePermission):
    """Event operations: the Organizers group, or any staff member."""

    message = 'You need organizer access to view this.'

    def has_permission(self, request, view):
        return in_group(request.user, ORGANIZERS_GROUP)


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
