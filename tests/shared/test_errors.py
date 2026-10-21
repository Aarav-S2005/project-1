"""Unit tests for domain exceptions."""

from shared.errors import (
    AuthenticationError,
    ConfigError,
    GatewayError,
    PolicyDeniedError,
    RouteNotFoundError,
    StepUpRequiredError,
    UpstreamError,
)


def test_error_attributes() -> None:
    """Verify status codes and detail attributes on domain exceptions."""
    gw_err = GatewayError("Base error", status_code=500, details={"k": "v"})
    assert gw_err.status_code == 500
    assert gw_err.details["k"] == "v"

    cfg_err = ConfigError("Invalid Mongo URL")
    assert cfg_err.status_code == 500

    route_err = RouteNotFoundError(path="/not/found", method="GET")
    assert route_err.status_code == 404
    assert route_err.details["path"] == "/not/found"

    auth_err = AuthenticationError("Missing Bearer Token")
    assert auth_err.status_code == 401

    step_up_err = StepUpRequiredError("MFA needed", session_id="s1")
    assert step_up_err.status_code == 403
    assert step_up_err.details["challenge"] == "step_up_mfa"

    policy_err = PolicyDeniedError("Blocked")
    assert policy_err.status_code == 403

    ups_err = UpstreamError("Service Unavailable", status_code=502)
    assert ups_err.status_code == 502
