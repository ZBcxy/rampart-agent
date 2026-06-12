"""Simple role-based access control for gateway endpoints.

Prevents every route from running without authorization checks.
Integrates with core.align.PolicyEngine for autonomy-level gating.
"""

from fastapi import HTTPException, status


class Authorizer:
    """Role-based authorizer with configurable permission sets.

    Built-in roles: admin, user, viewer.
    Permissions: read, write, delete, admin.
    """

    DEFAULT_ROLE_PERMISSIONS = {
        "admin": {"read", "write", "delete", "admin"},
        "user": {"read", "write"},
        "viewer": {"read"},
    }

    def __init__(self):
        self._role_permissions: dict[str, set[str]] = {
            role: set(perms)
            for role, perms in self.DEFAULT_ROLE_PERMISSIONS.items()
        }

    def check_permission(self, role: str, permission: str) -> bool:
        """Return True if the role holds the given permission."""
        return permission in self._role_permissions.get(role, set())

    def require_permission(self, role: str, permission: str):
        """Raise 403 if the role lacks the given permission."""
        if not self.check_permission(role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: '{role}' lacks '{permission}'",
            )

    def add_role(self, role: str, permissions: set[str]):
        """Register a custom role with the given permissions."""
        self._role_permissions[role] = set(permissions)

    def list_permissions(self, role: str) -> set[str]:
        """Return the permissions held by a role (empty set if unknown)."""
        return self._role_permissions.get(role, set())


# Module-level singleton
authorizer = Authorizer()
