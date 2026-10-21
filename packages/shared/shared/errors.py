"""Domain exceptions for Zero-Trust API Gateway."""

from typing import Any


class GatewayError(Exception):
    """Base exception for all gateway-related errors."""

    def __init__(
        self, message: str, status_code: int = 500, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ConfigError(GatewayError):
    """Raised when configuration validation or propagation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, status_code=500, details=details)


class RouteNotFoundError(GatewayError):
    """Raised when no matching upstream route is found for a request."""

    def __init__(self, path: str, method: str) -> None:
        super().__init__(
            f"No route matching '{method} {path}'",
            status_code=404,
            details={"path": path, "method": method},
        )


class UpstreamError(GatewayError):
    """Raised when upstream service communication fails."""

    def __init__(
        self, message: str, status_code: int = 502, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message, status_code=status_code, details=details)


class AuthenticationError(GatewayError):
    """Raised when subject authentication is missing or invalid."""

    def __init__(
        self, message: str = "Authentication required", details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message, status_code=401, details=details)


class StepUpRequiredError(GatewayError):
    """Raised when trust score band demands secondary authentication."""

    def __init__(
        self, message: str = "Step-up authentication required", session_id: str | None = None
    ) -> None:
        super().__init__(
            message,
            status_code=403,
            details={"challenge": "step_up_mfa", "session_id": session_id},
        )


class PolicyDeniedError(GatewayError):
    """Raised when ReBAC or trust policy explicitly denies access."""

    def __init__(
        self,
        message: str = "Access denied by zero-trust policy",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, status_code=403, details=details)
