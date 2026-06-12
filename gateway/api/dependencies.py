"""Gateway API dependencies — thin re-export layer for backward compatibility.

All authentication and authorization logic lives in gateway.security.
This module re-exports the shared symbols so existing import paths keep working.
"""

from gateway.security import get_current_user, get_request_id, require_authentication

__all__ = ["get_current_user", "get_request_id", "require_authentication"]
