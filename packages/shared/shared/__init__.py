"""Zero-Trust API Gateway shared library."""

from shared.config import Settings, get_settings
from shared.errors import (
    AuthenticationError,
    ConfigError,
    GatewayError,
    PolicyDeniedError,
    RouteNotFoundError,
    StepUpRequiredError,
    UpstreamError,
)
from shared.http import AsyncHttpClient
from shared.logging import configure_logging

__version__ = "0.1.0"

__all__ = [
    "AsyncHttpClient",
    "AuthenticationError",
    "ConfigError",
    "GatewayError",
    "PolicyDeniedError",
    "RouteNotFoundError",
    "Settings",
    "StepUpRequiredError",
    "UpstreamError",
    "configure_logging",
    "get_settings",
]
