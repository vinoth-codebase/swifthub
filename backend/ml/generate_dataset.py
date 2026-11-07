"""Generate synthetic historical quick-commerce dark-store order dataset for SLA/ETA modeling."""

import os
import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "item_count",
    "unique_aisles",
    "active_queue_depth",
    "idle_riders",
    "distance_km",
    "hour_of_day",
]


def generate_synthetic_dataset(n_samples: int = 2500, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    item_count = rng.integers(1, 15, size=n_samples)
    unique_aisles = np.minimum(item_count, rng.integers(1, 7, size=n_samples))
    active_queue_depth = rng.integers(0, 16, size=n_samples)
    idle_riders = rng.integers(0, 7, size=n_samples)
    distance_km = np.round(rng.uniform(0.3, 3.2, size=n_samples), 2)
    hour_of_day = rng.integers(6, 24, size=n_samples)

    # Peak congestion multiplier for Bangalore morning (8-10) and evening (18-21) windows
    is_peak = ((hour_of_day >= 8) & (hour_of_day <= 10)) | (
        (hour_of_day >= 18) & (hour_of_day <= 21)
    )
    peak_factor = np.where(is_peak, 1.24, 1.0)

    # Picking & packing duration (seconds)
    picking_sec = 45.0 + item_count * 11.5 + unique_aisles * 16.0
    queue_wait_sec = active_queue_depth * 17.5

    # Rider dispatch wait penalty when few/no idle riders are stationed at the hub
    rider_wait_sec = np.where(
        idle_riders == 0,
        135.0,
        np.where(idle_riders == 1, 55.0, np.maximum(10.0, 35.0 - idle_riders * 5.0)),
    )

    # Hyperlocal last-mile travel time (average speed ~16-20 km/h adjusted by peak congestion)
    travel_sec = (distance_km / 0.28) * 60.0 * peak_factor * 0.55

    noise = rng.normal(0.0, 26.0, size=n_samples)
    actual_eta_sec = np.clip(
        np.round(picking_sec + queue_wait_sec + rider_wait_sec + travel_sec + noise),
        180,
        1100,
    ).astype(int)

    sla_breached = (actual_eta_sec > 600).astype(int)

    df = pd.DataFrame(
        {
            "item_count": item_count,
            "unique_aisles": unique_aisles,
            "active_queue_depth": active_queue_depth,
            "idle_riders": idle_riders,
            "distance_km": distance_km,
            "hour_of_day": hour_of_day,
            "actual_eta_sec": actual_eta_sec,
            "sla_breached": sla_breached,
        }
    )
    return df


def main() -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, "historical_orders.csv")

    df = generate_synthetic_dataset(n_samples=2500, seed=42)
    df.to_csv(out_path, index=False)
    breach_rate = df["sla_breached"].mean() * 100
    print(
        f"Generated {len(df)} synthetic orders at {out_path} "
        f"(mean ETA={df['actual_eta_sec'].mean():.1f}s, SLA breach rate={breach_rate:.1f}%)"
    )


if __name__ == "__main__":
    main()
