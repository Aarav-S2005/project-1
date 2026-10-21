"""Behavioral feature extraction using Redis sliding windows, geo-velocity, and fingerprints."""

import hashlib
import math

import redis.asyncio as redis
from shared.schemas.trust import BehavioralFeatures, RequestTelemetry


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance between two GPS coordinates in kilometers."""
    r = 6371.0  # Earth radius in kilometers
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def ip_to_geo_coordinates(ip: str) -> tuple[float, float]:
    """Map IP address to deterministic latitude and longitude coordinates."""
    # Deterministic coordinate hashing for tests and synthetic simulation
    ip_hash = int(hashlib.md5(ip.encode("utf-8")).hexdigest(), 16)
    lat = ((ip_hash % 18000) / 100.0) - 90.0  # -90 to +90
    lon = (((ip_hash // 18000) % 36000) / 100.0) - 180.0  # -180 to +180
    return lat, lon


class BehavioralFeatureExtractor:
    """Extracts continuous behavioral telemetry signals from Redis."""

    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis = redis_client

    async def extract(self, telemetry: RequestTelemetry) -> BehavioralFeatures:
        """Derive 6-dimensional behavioral feature vector from incoming request telemetry."""
        now_ts = telemetry.timestamp.timestamp()
        session_id = telemetry.session_id

        # 1. Sliding Window Request Rates (10s and 60s)
        rate_key = f"session:{session_id}:req_timestamps"
        # Add current request timestamp as score and member
        req_id = f"{now_ts}:{telemetry.method}:{telemetry.path}"
        await self.redis.zadd(rate_key, {req_id: now_ts})
        # Expire older than 60s
        cutoff_60s = now_ts - 60.0
        cutoff_10s = now_ts - 10.0
        await self.redis.zremrangebyscore(rate_key, "-inf", cutoff_60s)
        await self.redis.expire(rate_key, 120)

        # Count requests in 10s and 60s
        count_10s = await self.redis.zcount(rate_key, cutoff_10s, "+inf")
        count_60s = await self.redis.zcount(rate_key, cutoff_60s, "+inf")

        req_rate_10s = float(count_10s) / 10.0
        req_rate_60s = float(count_60s) / 60.0
        rate_burst_ratio = req_rate_10s / (req_rate_60s + 0.1)

        # 2. Geo-Velocity (km/h)
        curr_lat, curr_lon = ip_to_geo_coordinates(telemetry.client_ip)
        geo_key = f"session:{session_id}:last_geo"
        last_geo = await self.redis.hgetall(geo_key)

        geo_velocity_kmh = 0.0
        if last_geo and b"lat" in last_geo and b"lon" in last_geo and b"ts" in last_geo:
            prev_lat = float(last_geo[b"lat"])
            prev_lon = float(last_geo[b"lon"])
            prev_ts = float(last_geo[b"ts"])
            time_delta_hours = (now_ts - prev_ts) / 3600.0

            if time_delta_hours > 0.0001:  # at least ~0.36 seconds
                dist_km = haversine_distance_km(prev_lat, prev_lon, curr_lat, curr_lon)
                geo_velocity_kmh = dist_km / time_delta_hours

        # Update geo state in Redis
        await self.redis.hset(
            geo_key,
            mapping={
                "lat": str(curr_lat),
                "lon": str(curr_lon),
                "ts": str(now_ts),
                "ip": telemetry.client_ip,
            },
        )
        await self.redis.expire(geo_key, 86400)

        # 3. TLS / Device Fingerprint Mismatch
        fp_key = f"session:{session_id}:fingerprints"
        raw_fp = f"{telemetry.tls_fingerprint}|{telemetry.user_agent}"
        fp_digest = hashlib.sha256(raw_fp.encode("utf-8")).hexdigest()[:16]

        seen_fingerprints = await self.redis.smembers(fp_key)
        tls_fingerprint_mismatch = 0.0

        if not seen_fingerprints:
            # First request in session -> register fingerprint
            await self.redis.sadd(fp_key, fp_digest)
            await self.redis.expire(fp_key, 86400 * 7)
        else:
            fp_bytes = fp_digest.encode("utf-8")
            if fp_bytes not in seen_fingerprints:
                # Fingerprint shifted mid-session! Anomaly flag = 1.0
                tls_fingerprint_mismatch = 1.0
                await self.redis.sadd(fp_key, fp_digest)

        # 4. Time-of-Day Deviation
        # Compute cyclical distance of hour from expected active peak (e.g. 14:00 UTC)
        req_hour = telemetry.timestamp.hour + (telemetry.timestamp.minute / 60.0)
        baseline_peak_hour = 14.0  # reference midpoint
        diff = abs(req_hour - baseline_peak_hour)
        cyclical_distance = min(diff, 24.0 - diff)
        time_of_day_deviation = cyclical_distance / 12.0  # normalized to [0.0, 1.0]

        return BehavioralFeatures(
            req_rate_10s=round(req_rate_10s, 3),
            req_rate_60s=round(req_rate_60s, 3),
            rate_burst_ratio=round(rate_burst_ratio, 3),
            geo_velocity_kmh=round(geo_velocity_kmh, 2),
            tls_fingerprint_mismatch=tls_fingerprint_mismatch,
            time_of_day_deviation=round(time_of_day_deviation, 3),
        )
