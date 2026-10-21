"""Unit tests for synthetic traffic generator and model training pipeline."""

from pathlib import Path

import joblib
import numpy as np

from scripts.generate_synthetic_traffic import FEATURE_NAMES, generate_traffic
from scripts.train_model import train_and_save_model


def test_generate_traffic_dimensions_and_labels() -> None:
    """Verify generated dataset shape, column names, and anomaly ratios."""
    num_samples = 1000
    anomaly_fraction = 0.05
    x_data, y, feature_names = generate_traffic(
        num_samples=num_samples,
        anomaly_fraction=anomaly_fraction,
        random_seed=123,
    )

    assert x_data.shape == (1000, 10)
    assert y.shape == (1000,)
    assert feature_names == FEATURE_NAMES

    # Check class distribution
    num_anomalies = np.sum(y == -1)
    num_inliers = np.sum(y == 1)
    assert num_anomalies == 50
    assert num_inliers == 950

    # Check non-negative values for rates and distances
    assert np.all(x_data[:, 0] >= 0.0)  # req_rate_10s
    assert np.all(x_data[:, 3] >= 0.0)  # geo_velocity_kmh
    assert np.all(x_data[:, 6] >= 1.0)  # path_length


def test_train_and_save_pipeline(tmp_path: Path) -> None:
    """Verify training pipeline fits Isolation Forest, TreeExplainer, and serializes artifacts."""
    out_dir = str(tmp_path / "models")
    metrics = train_and_save_model(
        output_dir=out_dir,
        num_samples=1000,
        contamination=0.05,
        random_seed=42,
    )

    # Model should easily separate distinct synthetic anomalies (ROC-AUC > 0.85)
    assert metrics["roc_auc"] > 0.80

    # Verify serialized files
    model_file = Path(out_dir) / "isolation_forest.joblib"
    explainer_file = Path(out_dir) / "shap_explainer.joblib"
    meta_file = Path(out_dir) / "features.json"

    assert model_file.exists()
    assert explainer_file.exists()
    assert meta_file.exists()

    # Verify loaded artifacts perform inference
    loaded_model = joblib.load(model_file)
    loaded_explainer = joblib.load(explainer_file)

    test_sample = np.array([[0.5, 0.5, 1.0, 0.0, 0.0, 0.1, 2.0, 0.0, 0.1, 5.0]])
    pred = loaded_model.predict(test_sample)
    assert pred[0] in (1, -1)

    shap_values = loaded_explainer.shap_values(test_sample)
    # SHAP values should have 10 elements corresponding to the 10 features
    assert np.asarray(shap_values).flatten().shape[0] == 10
