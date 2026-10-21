"""Unit tests for centralized configuration loading."""

import os
from unittest import mock

from shared.config import Settings, get_settings


def test_default_settings() -> None:
    """Verify default settings values match expected defaults."""
    settings = Settings()
    assert settings.control_plane_port == 3002
    assert settings.data_plane_port == 3003
    assert settings.config_poll_interval_seconds == 4
    assert settings.mongo_uri == "mongodb://localhost:27017"
    assert settings.redis_port == 6379
    assert settings.spicedb_grpc_endpoint == "localhost:50051"
    assert settings.band_threshold_narrow == 0.85
    assert settings.band_threshold_step_up == 0.60
    assert settings.band_threshold_deny == 0.40


def test_custom_environment_override() -> None:
    """Verify environment variables properly override default settings."""
    env_overrides = {
        "CONTROL_PLANE_PORT": "9002",
        "DATA_PLANE_PORT": "9003",
        "CONFIG_POLL_INTERVAL_SECONDS": "10",
        "REDIS_HOST": "redis.internal",
    }
    with mock.patch.dict(os.environ, env_overrides, clear=False):
        settings = Settings()
        assert settings.control_plane_port == 9002
        assert settings.data_plane_port == 9003
        assert settings.config_poll_interval_seconds == 10
        assert settings.redis_host == "redis.internal"


def test_cached_singleton() -> None:
    """Verify get_settings returns consistent cached instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
