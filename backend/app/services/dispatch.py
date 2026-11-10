from typing import Optional
from sqlalchemy.orm import Session

from app.models import Order, Rider, Store
from app.services.ml_inference import haversine_km


def assign_nearest_idle_rider(db: Session, order: Order) -> Optional[Rider]:
    """Find the nearest IDLE rider for the order's hub and assign them to the order."""
    if order.rider_id is not None:
        return db.query(Rider).filter(Rider.id == order.rider_id).first()

    store = db.query(Store).filter(Store.id == order.store_id).first()
    if not store:
        return None

    idle_riders = (
        db.query(Rider)
        .filter(Rider.store_id == order.store_id, Rider.status == "IDLE")
        .all()
    )
    if not idle_riders:
        return None

    nearest_rider = min(
        idle_riders,
        key=lambda r: haversine_km(store.lat, store.lng, r.current_lat, r.current_lng),
    )
    nearest_rider.status = "ASSIGNED"
    order.rider_id = nearest_rider.id
    return nearest_rider
