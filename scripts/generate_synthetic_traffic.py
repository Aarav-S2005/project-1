"""Synthetic traffic generator producing baseline and anomalous feature vectors."""

import numpy as np

FEATURE_NAMES = [
    "req_rate_10s",
    "req_rate_60s",
    "rate_burst_ratio",
    "geo_velocity_kmh",
    "tls_fingerprint_mismatch",
    "time_of_day_deviation",
    "path_length",
    "path_novelty",
    "privilege_shortcut_score",
    "intermediate_node_degree",
]


def generate_traffic(
    num_samples: int = 10000,
    anomaly_fraction: float = 0.05,
    random_seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Generate synthetic behavioral and graph-structural feature vectors.

    Returns:
        X: numpy array of shape (num_samples, 10) containing feature values.
        y: numpy array of shape (num_samples,) containing ground truth labels
           (1 for normal, -1 for anomaly, matching scikit-learn conventions).
        feature_names: list of feature names matching array columns.
    """
    rng = np.random.default_rng(random_seed)

    num_anomalies = int(num_samples * anomaly_fraction)
    num_benign = num_samples - num_anomalies

    # 1. Generate Benign Baseline Traffic (95%)
    benign_rate_60s = rng.uniform(0.1, 2.0, size=num_benign)
    # 10s rate closely tracks 60s rate with small noise
    benign_rate_10s = np.clip(benign_rate_60s + rng.normal(0, 0.2, size=num_benign), 0.05, 3.5)
    benign_burst_ratio = benign_rate_10s / (benign_rate_60s + 0.1)

    # Geo-velocity: static or small local jitter (0 to 15 km/h)
    benign_geo_velocity = rng.exponential(scale=2.0, size=num_benign)

    # Fingerprints: consistent across session
    benign_tls_mismatch = np.zeros(num_benign)

    # Time-of-day: standard business and active hours (low deviation)
    benign_time_dev = rng.beta(a=1.5, b=5.0, size=num_benign)

    # Graph structural: normal organizational delegations (depth 2-4)
    benign_path_length = rng.choice([2.0, 3.0, 4.0], size=num_benign, p=[0.6, 0.3, 0.1])
    benign_path_novelty = np.zeros(num_benign)  # routine known paths
    benign_priv_shortcut = rng.uniform(0.05, 0.2, size=num_benign)
    benign_node_degree = rng.uniform(3.0, 10.0, size=num_benign)

    x_benign = np.column_stack(
        [
            benign_rate_10s,
            benign_rate_60s,
            benign_burst_ratio,
            benign_geo_velocity,
            benign_tls_mismatch,
            benign_time_dev,
            benign_path_length,
            benign_path_novelty,
            benign_priv_shortcut,
            benign_node_degree,
        ]
    )
    y_benign = np.ones(num_benign, dtype=int)  # 1 = inlier

    # 2. Generate Anomalous Attack Traffic (5%)
    # Start from baseline and inject distinct attack archetypes
    x_anomaly = np.copy(x_benign[:num_anomalies])
    y_anomaly = -np.ones(num_anomalies, dtype=int)  # -1 = anomaly

    # Partition anomalies across 4 realistic attack vectors
    quarters = num_anomalies // 4

    # Attack Type 1: High rate burst / credential stuffing attack
    x_anomaly[:quarters, 0] = rng.uniform(15.0, 45.0, size=quarters)  # req_rate_10s
    x_anomaly[:quarters, 2] = rng.uniform(5.0, 15.0, size=quarters)  # burst ratio

    # Attack Type 2: Impossible travel / intercontinental geo-velocity jump
    x_anomaly[quarters : 2 * quarters, 3] = rng.uniform(800.0, 2500.0, size=quarters)

    # Attack Type 3: Session hijacking / TLS & UA fingerprint mutation
    x_anomaly[2 * quarters : 3 * quarters, 4] = 1.0  # tls_fingerprint_mismatch
    x_anomaly[2 * quarters : 3 * quarters, 5] = rng.uniform(0.7, 1.0, size=quarters)

    # Attack Type 4: Graph privilege-escalation shortcut & novel traversal path
    x_anomaly[3 * quarters :, 6] = 1.0  # path_length = 1 (direct bypass)
    x_anomaly[3 * quarters :, 7] = 1.0  # path_novelty = 1.0 (novel edge)
    x_anomaly[3 * quarters :, 8] = rng.uniform(0.8, 1.0, size=num_anomalies - 3 * quarters)

    # Combine datasets and shuffle
    x_data = np.vstack([x_benign, x_anomaly])
    y = np.concatenate([y_benign, y_anomaly])

    perm = rng.permutation(num_samples)
    return x_data[perm], y[perm], FEATURE_NAMES


if __name__ == "__main__":
    x_data, y_labels, names = generate_traffic(10000, 0.05)
    print(f"Generated {x_data.shape[0]} samples with {len(names)} features.")
    print(f"Anomalies: {np.sum(y_labels == -1)}, Inliers: {np.sum(y_labels == 1)}")
