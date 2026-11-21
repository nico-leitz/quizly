from rest_framework.permissions import BasePermission


class IsQuizOwner(BasePermission):
    """Allow access only to the authenticated owner of a quiz."""

    message = "Access denied - this quiz does not belong to you."

    def has_object_permission(self, request, view, obj):
        """Return True if the requested quiz belongs to the user."""
        return obj.user == request.user