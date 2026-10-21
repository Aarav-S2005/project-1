"""Offline model training script for Isolation Forest and SHAP TreeExplainer."""

import json
from pathlib import Path

import joblib
import shap
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report, roc_auc_score

try:
    from scripts.generate_synthetic_traffic import generate_traffic
except ModuleNotFoundError:
    from generate_synthetic_traffic import generate_traffic  # type: ignore


def train_and_save_model(
    output_dir: str = "models",
    num_samples: int = 10000,
    contamination: float = 0.05,
    random_seed: int = 42,
) -> dict[str, float]:
    """Train Isolation Forest and SHAP explainer on synthetic traffic and serialize artifacts."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print(f"Generating {num_samples} synthetic traffic samples...")
    x_data, y, feature_names = generate_traffic(
        num_samples=num_samples,
        anomaly_fraction=contamination,
        random_seed=random_seed,
    )

    print("Fitting Isolation Forest model...")
    model = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=random_seed,
        n_jobs=-1,
    )
    model.fit(x_data)

    # Evaluate model
    y_pred = model.predict(x_data)
    scores = -model.score_samples(x_data)  # higher = more anomalous
    auc = float(roc_auc_score(y == -1, scores))
    print(f"Model ROC-AUC Score: {auc:.4f}")
    print("\nClassification Report (Ground Truth vs Isolation Forest):")
    print(classification_report(y, y_pred, target_names=["Anomaly (-1)", "Inlier (1)"]))

    print("Building SHAP TreeExplainer...")
    # Use TreeExplainer directly on fitted Isolation Forest
    explainer = shap.TreeExplainer(model)

    # Save artifacts
    model_path = out_path / "isolation_forest.joblib"
    explainer_path = out_path / "shap_explainer.joblib"
    features_path = out_path / "features.json"

    joblib.dump(model, model_path)
    joblib.dump(explainer, explainer_path)

    with open(features_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "features": feature_names,
                "contamination": contamination,
                "n_estimators": 100,
                "roc_auc": round(auc, 4),
            },
            f,
            indent=2,
        )

    print(f"Successfully serialized model artifacts to {out_path.resolve()}/")
    return {"roc_auc": auc}


if __name__ == "__main__":
    train_and_save_model()
