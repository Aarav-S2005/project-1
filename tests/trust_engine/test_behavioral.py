"""Unit tests for BehavioralFeatureExtractor."""

from datetime import UTC, datetime, timedelta

import pytest
import redis.asyncio as redis
from shared.schemas.trust import RequestTelemetry
from trust_engine.features.behavioral import (
    BehavioralFeatureExtractor,
    haversine_distance_km,
    ip_to_geo_coordinates,
)


def test_haversine_math() -> None:
    """Verify great-circle distance math between London and Paris (~343 km)."""
    # London: 51.5074 N, 0.1278 W; Paris: 48.8566 N, 2.3522 E
    dist = haversine_distance_km(51.5074, -0.1278, 48.8566, 2.3522)
    assert 340.0 < dist < 350.0


def test_ip_to_geo_determinism() -> None:
    """Verify deterministic latitude and longitude derivation from IP."""
    lat1, lon1 = ip_to_geo_coordinates("198.51.100.1")
    lat2, lon2 = ip_to_geo_coordinates("198.51.100.1")
    assert lat1 == lat2
    assert lon1 == lon2
    assert -90.0 <= lat1 <= 90.0
    assert -180.0 <= lon1 <= 180.0


@pytest.mark.asyncio
async def test_sliding_window_rate_and_burst(fake_redis: redis.Redis) -> None:
    """Verify sliding rate counters and burst ratio calculation."""
    extractor = BehavioralFeatureExtractor(fake_redis)
    base_time = datetime(2026, 10, 19, 12, 0, 0, tzinfo=UTC)

    # Send 5 requests within 2 seconds
    for i in range(5):
        telemetry = RequestTelemetry(
            session_id="sess_rate_test",
            subject_id="user:alice",
            client_ip="192.168.1.10",
            method="GET",
            path=f"/doc/{i}",
            timestamp=base_time + timedelta(seconds=i * 0.4),
        )
        features = await extractor.extract(telemetry)

    # 5 requests in 10s window -> req_rate_10s = 0.5 req/s
    assert features.req_rate_10s == 0.5
    # 5 requests in 60s window -> req_rate_60s = 5 / 60 ≈ 0.083
    assert features.req_rate_60s > 0.08
    # Burst ratio = 0.5 / (0.083 + 0.1) ≈ 2.7
    assert features.rate_burst_ratio > 1.5


@pytest.mark.asyncio
async def test_geo_velocity_impossible_travel(fake_redis: redis.Redis) -> None:
    """Verify high geo-velocity detection when client IP jumps geographic distance rapidly."""
    extractor = BehavioralFeatureExtractor(fake_redis)
    t0 = datetime(2026, 10, 19, 12, 0, 0, tzinfo=UTC)

    # First request from IP 1 (initializes location, velocity = 0)
    tel1 = RequestTelemetry(
        session_id="sess_geo_test",
        subject_id="user:bob",
        client_ip="1.1.1.1",
        method="GET",
        path="/api/data",
        timestamp=t0,
    )
    feat1 = await extractor.extract(tel1)
    assert feat1.geo_velocity_kmh == 0.0

    # Second request 1 minute later from a drastically different IP across the globe
    t1 = t0 + timedelta(minutes=1)
    tel2 = RequestTelemetry(
        session_id="sess_geo_test",
        subject_id="user:bob",
        client_ip="203.0.113.195",
        method="GET",
        path="/api/data",
        timestamp=t1,
    )
    feat2 = await extractor.extract(tel2)

    # 1 minute delta across different hashed continents yields impossible
    # travel velocity (> 1000 km/h)
    assert feat2.geo_velocity_kmh > 500.0


@pytest.mark.asyncio
async def test_fingerprint_mismatch_detection(fake_redis: redis.Redis) -> None:
    """Verify TLS and User-Agent fingerprint shift detection within same session."""
    extractor = BehavioralFeatureExtractor(fake_redis)
    t0 = datetime(2026, 10, 19, 12, 0, 0, tzinfo=UTC)

    # Initial request establishes baseline session fingerprint
    tel1 = RequestTelemetry(
        session_id="sess_fp_test",
        subject_id="user:charlie",
        client_ip="10.0.0.1",
        user_agent="Mozilla/5.0 (Windows NT 10.0)",
        tls_fingerprint="tls_digest_v1",
        method="GET",
        path="/api/home",
        timestamp=t0,
    )
    feat1 = await extractor.extract(tel1)
    assert feat1.tls_fingerprint_mismatch == 0.0

    # Subsequent request with same credentials and headers -> mismatch is 0.0
    tel2 = RequestTelemetry(
        session_id="sess_fp_test",
        subject_id="user:charlie",
        client_ip="10.0.0.1",
        user_agent="Mozilla/5.0 (Windows NT 10.0)",
        tls_fingerprint="tls_digest_v1",
        method="GET",
        path="/api/settings",
        timestamp=t0 + timedelta(seconds=5),
    )
    feat2 = await extractor.extract(tel2)
    assert feat2.tls_fingerprint_mismatch == 0.0

    # Attacker hijacks session token with different curl user-agent or TLS cipher suite
    tel3 = RequestTelemetry(
        session_id="sess_fp_test",
        subject_id="user:charlie",
        client_ip="10.0.0.1",
        user_agent="curl/8.4.0",
        tls_fingerprint="tls_digest_attacker_kali",
        method="GET",
        path="/api/admin",
        timestamp=t0 + timedelta(seconds=10),
    )
    feat3 = await extractor.extract(tel3)
    assert feat3.tls_fingerprint_mismatch == 1.0
