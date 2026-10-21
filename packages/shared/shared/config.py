"""Central configuration loading via Pydantic BaseSettings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for Zero-Trust API Gateway services."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Service Bindings
    control_plane_host: str = Field(default="0.0.0.0", alias="CONTROL_PLANE_HOST")
    control_plane_port: int = Field(default=3002, alias="CONTROL_PLANE_PORT")
    data_plane_host: str = Field(default="0.0.0.0", alias="DATA_PLANE_HOST")
    data_plane_port: int = Field(default=3003, alias="DATA_PLANE_PORT")

    # Data Plane -> Control Plane Polling
    control_plane_url: str = Field(default="http://localhost:3002", alias="CONTROL_PLANE_URL")
    config_poll_interval_seconds: int = Field(default=4, alias="CONFIG_POLL_INTERVAL_SECONDS")

    # MongoDB (Host localhost:27017 or Docker host.docker.internal:27017)
    mongo_uri: str = Field(default="mongodb://localhost:27017", alias="MONGO_URI")
    mongo_db_name: str = Field(default="zero_trust_gateway", alias="MONGO_DB_NAME")

    # Redis (Features & session trust state)
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_password: str | None = Field(default=None, alias="REDIS_PASSWORD")

    # SpiceDB (ReBAC store)
    spicedb_grpc_endpoint: str = Field(default="localhost:50051", alias="SPICEDB_GRPC_ENDPOINT")
    spicedb_preshared_key: str = Field(
        default="secret_preshared_key", alias="SPICEDB_PRESHARED_KEY"
    )
    spicedb_insecure: bool = Field(default=True, alias="SPICEDB_INSECURE")

    # Anomaly Model & Files
    model_path: str = Field(default="models/isolation_forest.joblib", alias="MODEL_PATH")
    explainer_path: str = Field(default="models/shap_explainer.joblib", alias="EXPLAINER_PATH")

    # Trust Scoring Formula Parameters
    trust_half_life_seconds: float = Field(default=300.0, alias="TRUST_HALF_LIFE_SECONDS")
    trust_anomaly_weight: float = Field(default=0.35, alias="TRUST_ANOMALY_WEIGHT")

    # Decision Bands Thresholds
    band_threshold_narrow: float = Field(default=0.85, alias="BAND_THRESHOLD_NARROW")
    band_threshold_step_up: float = Field(default=0.60, alias="BAND_THRESHOLD_STEP_UP")
    band_threshold_deny: float = Field(default=0.40, alias="BAND_THRESHOLD_DENY")
    narrow_ttl_seconds: int = Field(default=900, alias="NARROW_TTL_SECONDS")

    # Logging & Environment
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", alias="LOG_LEVEL"
    )
    environment: Literal["development", "testing", "production"] = Field(
        default="development", alias="ENVIRONMENT"
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton instance of application settings."""
    return Settings()
