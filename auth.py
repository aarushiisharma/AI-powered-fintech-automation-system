"""
RBAC — Role-Based Access Control with API Key authentication.
Three roles: TIER1_SUPPORT, COMPLIANCE_MANAGER, SYSTEM_ADMIN.
Auth via X-API-Key header. Tracks user identity for audit logging.
"""

from enum import Enum
from pydantic import BaseModel
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader


class Role(str, Enum):
    TIER1_SUPPORT = "TIER1_SUPPORT"
    COMPLIANCE_MANAGER = "COMPLIANCE_MANAGER"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"


class User(BaseModel):
    username: str
    role: Role
    api_key: str
    is_active: bool = True


# --- User registry (swap for DB in production) ---
USERS = {
    "key-tier1-support": User(
        username="agent_sarah",
        role=Role.TIER1_SUPPORT,
        api_key="key-tier1-support",
    ),
    "key-compliance-mgr": User(
        username="manager_james",
        role=Role.COMPLIANCE_MANAGER,
        api_key="key-compliance-mgr",
    ),
    "key-system-admin": User(
        username="system_admin",
        role=Role.SYSTEM_ADMIN,
        api_key="key-system-admin",
    ),
}

# Header extractor
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(api_key: str = Security(api_key_header)) -> User:
    """Extract and validate user from X-API-Key header."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )
    user = USERS.get(api_key)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )
    return user


def require_role(*allowed_roles: Role):
    """Dependency factory: checks if authenticated user has one of the allowed roles."""
    async def _check_role(user: User = Security(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role.value}' does not have permission. Required: {[r.value for r in allowed_roles]}",
            )
        return user
    return _check_role
