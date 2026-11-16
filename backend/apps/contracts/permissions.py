from rest_framework import permissions


class IsAdminOrReadOnlyDelete(permissions.BasePermission):
    """
    legal_reviewer and admin can both create/update/query contracts.
    Only admin can delete.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if view.action == "destroy":
            return request.user.is_admin or request.user.is_superuser
        return True

    def has_object_permission(self, request, view, obj):
        if view.action == "destroy":
            return request.user.is_admin or request.user.is_superuser
        return True
