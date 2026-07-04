from rest_framework import permissions


def role(user):
    return getattr(getattr(user, "profile", None), "role", None)


class IsHROrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return role(request.user) == "hr"


class IsManagerOrHR(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated) and role(request.user) in (
            "manager",
            "hr",
        )
