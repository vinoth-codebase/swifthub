import json
import math
import os
from datetime import datetime, timezone
from typing import Optional, Tuple

import joblib
import pandas as pd

from app.config import settings

FEATURE_COLUMNS = [
    "item_count",
    "unique_aisles",
    "active_queue_depth",
    "idle_riders",
    "distance_km",
    "hour_of_day",
]


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    earth_radius_km = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(earth_radius_km * c, 3)


class SLAPredictor:
    def __init__(self, model_dir: Optional[str] = None) -> None:
        self.model_dir = model_dir or settings.MODEL_DIR
        self.eta_model = None
        self.sla_model = None
        self.metrics: dict = {}

    def load(self) -> bool:
        eta_path = os.path.join(self.model_dir, "eta_model.joblib")
        sla_path = os.path.join(self.model_dir, "sla_risk_model.joblib")
        metrics_path = os.path.join(self.model_dir, "metrics.json")

        if os.path.exists(eta_path) and os.path.exists(sla_path):
            self.eta_model = joblib.load(eta_path)
            self.sla_model = joblib.load(sla_path)
        if os.path.exists(metrics_path):
            with open(metrics_path, "r", encoding="utf-8") as f:
                self.metrics = json.load(f)
        return self.eta_model is not None and self.sla_model is not None

    def predict(
        self,
        item_count: int,
        unique_aisles: int,
        active_queue_depth: int,
        idle_riders: int,
        distance_km: float,
        hour_of_day: Optional[int] = None,
    ) -> Tuple[int, float]:
        if self.eta_model is None or self.sla_model is None:
            self.load()

        if hour_of_day is None:
            hour_of_day = datetime.now(timezone.utc).hour

        clamped_dist = max(0.1, min(15.0, float(distance_km)))

        if self.eta_model is not None and self.sla_model is not None:
            features_df = pd.DataFrame(
                [
                    {
                        "item_count": int(item_count),
                        "unique_aisles": int(unique_aisles),
                        "active_queue_depth": int(active_queue_depth),
                        "idle_riders": int(idle_riders),
                        "distance_km": clamped_dist,
                        "hour_of_day": int(hour_of_day),
                    }
                ],
                columns=FEATURE_COLUMNS,
            )
            eta_pred = float(self.eta_model.predict(features_df)[0])
            sla_prob = float(self.sla_model.predict_proba(features_df)[0][1])
            predicted_eta = int(max(180, min(1200, round(eta_pred))))
            sla_risk = round(max(0.0, min(1.0, sla_prob)), 4)
            return predicted_eta, sla_risk

        # Deterministic heuristic fallback if serialized models are unavailable
        heuristic_eta = int(
            max(
                180,
                min(
                    1200,
                    round(
                        120
                        + item_count * 12
                        + unique_aisles * 15
                        + active_queue_depth * 18
                        + clamped_dist * 110
                        + (100 if idle_riders == 0 else 20)
                    ),
                ),
            )
        )
        heuristic_risk = round(max(0.0, min(1.0, (heuristic_eta - 360) / 360.0)), 4)
        return heuristic_eta, heuristic_risk


sla_predictor = SLAPredictor()
