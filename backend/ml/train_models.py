"""Train and serialize Scikit-learn ETA regressor and SLA breach classifier."""

import json
import os
import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.metrics import accuracy_score, mean_absolute_error, r2_score, roc_auc_score
from sklearn.model_selection import train_test_split

from generate_dataset import FEATURE_COLUMNS, generate_synthetic_dataset


def train_and_save() -> dict:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(base_dir, "data", "historical_orders.csv")
    artifacts_dir = os.path.join(base_dir, "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)

    if os.path.exists(data_path):
        df = pd.read_csv(data_path)
    else:
        df = generate_synthetic_dataset(n_samples=2500, seed=42)

    X = df[FEATURE_COLUMNS]
    y_eta = df["actual_eta_sec"]
    y_sla = df["sla_breached"]

    X_train, X_test, y_eta_train, y_eta_test, y_sla_train, y_sla_test = train_test_split(
        X, y_eta, y_sla, test_size=0.2, random_state=42
    )

    eta_model = GradientBoostingRegressor(
        n_estimators=120,
        max_depth=4,
        learning_rate=0.08,
        random_state=42,
    )
    eta_model.fit(X_train, y_eta_train)
    eta_preds = eta_model.predict(X_test)
    eta_mae = float(mean_absolute_error(y_eta_test, eta_preds))
    eta_r2 = float(r2_score(y_eta_test, eta_preds))

    sla_model = RandomForestClassifier(
        n_estimators=120,
        max_depth=8,
        random_state=42,
    )
    sla_model.fit(X_train, y_sla_train)
    sla_probs = sla_model.predict_proba(X_test)[:, 1]
    sla_preds = (sla_probs >= 0.5).astype(int)
    sla_acc = float(accuracy_score(y_sla_test, sla_preds))
    sla_auc = float(roc_auc_score(y_sla_test, sla_probs))

    eta_path = os.path.join(artifacts_dir, "eta_model.joblib")
    sla_path = os.path.join(artifacts_dir, "sla_risk_model.joblib")
    metrics_path = os.path.join(artifacts_dir, "metrics.json")

    joblib.dump(eta_model, eta_path, compress=3)
    joblib.dump(sla_model, sla_path, compress=3)

    metrics = {
        "features": FEATURE_COLUMNS,
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "eta_regressor": {
            "algorithm": "GradientBoostingRegressor",
            "mae_sec": round(eta_mae, 2),
            "r2": round(eta_r2, 4),
        },
        "sla_classifier": {
            "algorithm": "RandomForestClassifier",
            "accuracy": round(sla_acc, 4),
            "roc_auc": round(sla_auc, 4),
        },
    }
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(
        f"Models saved to {artifacts_dir} | "
        f"ETA MAE={eta_mae:.2f}s R2={eta_r2:.4f} | "
        f"SLA Acc={sla_acc:.4f} AUC={sla_auc:.4f}"
    )
    return metrics


if __name__ == "__main__":
    train_and_save()
