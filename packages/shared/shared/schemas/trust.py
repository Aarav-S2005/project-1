"""Schemas for request telemetry, extracted feature vectors, and trust scoring."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class RequestTelemetry(BaseModel):
    """Contextual metadata captured from an incoming HTTP request."""

    session_id: str = Field(description="Unique session/token tracking identifier")
    subject_id: str = Field(description="Subject principal, e.g. user:alice")
    client_ip: str = Field(description="Originating client IP address")
    user_agent: str = Field(default="", description="Client User-Agent header")
    tls_fingerprint: str = Field(default="", description="TLS cipher or header digest")
    method: str = Field(description="HTTP request method")
    path: str = Field(description="Request path")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BehavioralFeatures(BaseModel):
    """Behavioral telemetry metrics extracted over rolling Redis windows."""

    req_rate_10s: float = Field(default=0.0, description="Requests/sec over 10s sliding window")
    req_rate_60s: float = Field(default=0.0, description="Requests/sec over 60s sliding window")
    rate_burst_ratio: float = Field(default=1.0, description="Ratio of 10s rate to 60s rate")
    geo_velocity_kmh: float = Field(
        default=0.0, description="Derived speed between consecutive locations (km/h)"
    )
    tls_fingerprint_mismatch: float = Field(
        default=0.0, description="1.0 if fingerprint shifted, else 0.0"
    )
    time_of_day_deviation: float = Field(
        default=0.0, description="Deviation from user baseline activity hour"
    )


class GraphFeatures(BaseModel):
    """Graph-structural features derived from SpiceDB relationship traversal."""

    path_length: float = Field(
        default=1.0, description="Number of edges/hops in ReBAC resolution tree"
    )
    path_novelty: float = Field(
        default=0.0, description="1.0 if path structure has never been seen for subject"
    )
    privilege_shortcut_score: float = Field(
        default=0.0, description="Score indicating potential hierarchy bypass"
    )
    intermediate_node_degree: float = Field(
        default=1.0, description="Degree of intermediate delegation nodes"
    )


class FeatureVector(BaseModel):
    """Combined feature vector consumed by anomaly detection model and SHAP."""

    behavioral: BehavioralFeatures = Field(default_factory=BehavioralFeatures)
    graph: GraphFeatures = Field(default_factory=GraphFeatures)

    def to_array(self) -> list[float]:
        """Convert features to canonical ordered list matching model inputs."""
        return [
            self.behavioral.req_rate_10s,
            self.behavioral.req_rate_60s,
            self.behavioral.rate_burst_ratio,
            self.behavioral.geo_velocity_kmh,
            self.behavioral.tls_fingerprint_mismatch,
            self.behavioral.time_of_day_deviation,
            self.graph.path_length,
            self.graph.path_novelty,
            self.graph.privilege_shortcut_score,
            self.graph.intermediate_node_degree,
        ]

    def to_dict(self) -> dict[str, float]:
        """Convert features to flat key-value dictionary."""
        return {
            "req_rate_10s": self.behavioral.req_rate_10s,
            "req_rate_60s": self.behavioral.req_rate_60s,
            "rate_burst_ratio": self.behavioral.rate_burst_ratio,
            "geo_velocity_kmh": self.behavioral.geo_velocity_kmh,
            "tls_fingerprint_mismatch": self.behavioral.tls_fingerprint_mismatch,
            "time_of_day_deviation": self.behavioral.time_of_day_deviation,
            "path_length": self.graph.path_length,
            "path_novelty": self.graph.path_novelty,
            "privilege_shortcut_score": self.graph.privilege_shortcut_score,
            "intermediate_node_degree": self.graph.intermediate_node_degree,
        }


class TrustScoreResult(BaseModel):
    """Outcome of trust scoring evaluation for a session."""

    session_id: str
    subject_id: str
    previous_score: float
    current_score: float
    score_delta: float
    is_anomaly: bool
    anomaly_severity: float
    feature_vector: FeatureVector
    shap_attributions: dict[str, float] = Field(default_factory=dict)
