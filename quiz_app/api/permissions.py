from rest_framework.permissions import BasePermission


class IsQuizOwner(BasePermission):
    message = "Access denied - this quiz does not belong to you."

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user