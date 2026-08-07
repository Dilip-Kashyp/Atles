"""
Domain shared: structured exception hierarchy.

All domain-level errors inherit from AtlasError.
API layers catch these and convert to appropriate HTTP responses.

Do not raise raw HTTPException from inside domain services.
Domain services raise domain errors; the API layer maps them to HTTP.
"""
from typing import Any


class AtlasError(Exception):
    """Base class for all Atlas domain errors."""

    def __init__(self, message: str, code: str | None = None, **context: Any) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.context = context

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code!r}, message={self.message!r})"


# ─── Not Found ────────────────────────────────────────────────────────────────

class NotFoundError(AtlasError):
    """Raised when a requested resource does not exist or has been soft-deleted."""
    pass


class UserNotFoundError(NotFoundError):
    pass


class WorkspaceNotFoundError(NotFoundError):
    pass


class OrganizationNotFoundError(NotFoundError):
    pass


class InvitationNotFoundError(NotFoundError):
    pass


class SessionNotFoundError(NotFoundError):
    pass


# ─── Authentication ────────────────────────────────────────────────────────────

class AuthenticationError(AtlasError):
    """Raised when authentication fails (invalid credentials, expired token, etc.)."""
    pass


class InvalidTokenError(AuthenticationError):
    pass


class ExpiredTokenError(AuthenticationError):
    pass


class TokenReuseDetectedError(AuthenticationError):
    """
    Raised when a refresh token is presented after it has already been used.
    This is a strong signal of token theft. All user sessions should be revoked.
    """
    pass


class OAuthError(AuthenticationError):
    """Raised for errors in the OAuth exchange or state validation."""
    pass


# ─── Authorization ─────────────────────────────────────────────────────────────

class AuthorizationError(AtlasError):
    """Raised when an authenticated user lacks permission to perform an action."""
    pass


class InsufficientPermissionsError(AuthorizationError):
    def __init__(self, required_permission: str, **context: Any) -> None:
        super().__init__(
            f"Missing required permission: {required_permission}",
            code="INSUFFICIENT_PERMISSIONS",
            required_permission=required_permission,
            **context,
        )


class WorkspaceMembershipRequiredError(AuthorizationError):
    pass


# ─── Conflict ─────────────────────────────────────────────────────────────────

class ConflictError(AtlasError):
    """Raised when an operation would violate a uniqueness constraint."""
    pass


class DuplicateEmailError(ConflictError):
    pass


class DuplicateSlugError(ConflictError):
    pass


class AlreadyMemberError(ConflictError):
    pass


class AccountAlreadyLinkedError(ConflictError):
    """Raised when attempting to link an OAuth account already linked to another user."""
    pass


# ─── Validation ───────────────────────────────────────────────────────────────

class ValidationError(AtlasError):
    """Raised for invalid input that does not fit business rules."""
    pass


class InvitationExpiredError(ValidationError):
    pass


class InvitationAlreadyAcceptedError(ValidationError):
    pass


class InvitationRevokedError(ValidationError):
    pass


# ─── Rate Limiting ────────────────────────────────────────────────────────────

class RateLimitExceededError(AtlasError):
    """Raised when a rate limit has been exceeded."""
    pass
