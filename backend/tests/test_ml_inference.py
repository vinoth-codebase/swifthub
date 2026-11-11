from app.services.ml_inference import SLAPredictor


def test_ml_models_load_and_return_bounded_predictions():
    predictor = SLAPredictor()
    loaded = predictor.load()
    assert loaded is True

    eta_low, risk_low = predictor.predict(
        item_count=1,
        unique_aisles=1,
        active_queue_depth=0,
        idle_riders=5,
        distance_km=0.4,
        hour_of_day=14,
    )
    assert 180 <= eta_low <= 1200
    assert 0.0 <= risk_low <= 1.0

    eta_high, risk_high = predictor.predict(
        item_count=12,
        unique_aisles=6,
        active_queue_depth=14,
        idle_riders=0,
        distance_km=3.0,
        hour_of_day=19,
    )
    assert 180 <= eta_high <= 1200
    assert 0.0 <= risk_high <= 1.0

    # High-load peak order should have substantially higher ETA and breach risk
    assert eta_high > eta_low
    assert risk_high > risk_low
