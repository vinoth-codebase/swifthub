from typing import Dict, Optional, Set
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models import Order, OrderEvent, OrderItem, Rider
from app.services.inventory import (
    release_reserved_on_delivery,
    restore_inventory_atomic,
)

VALID_STATUSES: Set[str] = {
    "PLACED",
    "PICKING",
    "PACKED",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
    "CANCELLED",
}

ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
    "PLACED": {"PICKING", "CANCELLED"},
    "PICKING": {"PACKED", "CANCELLED"},
    "PACKED": {"OUT_FOR_DELIVERY", "CANCELLED"},
    "OUT_FOR_DELIVERY": {"DELIVERED"},
    "DELIVERED": set(),
    "CANCELLED": set(),
}


def validate_transition(current_status: str, target_status: str) -> None:
    if target_status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown order status '{target_status}'.",
        )
    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid status transition from '{current_status}' to '{target_status}'. "
                f"Allowed next states: {sorted(allowed) if allowed else 'none'}."
            ),
        )


def transition_order_status(
    db: Session,
    order_id: int,
    target_status: str,
    note: Optional[str] = None,
) -> Order:
    normalized_target = target_status.strip().upper()
    order = (
        db.query(Order)
        .options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.rider),
            joinedload(Order.store),
            joinedload(Order.events),
        )
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    previous_status = order.status
    validate_transition(previous_status, normalized_target)

    order.status = normalized_target

    if normalized_target == "CANCELLED":
        restore_inventory_atomic(db, order)
        if order.rider_id is not None:
            rider = db.query(Rider).filter(Rider.id == order.rider_id).first()
            if rider:
                rider.status = "IDLE"
            order.rider_id = None
    elif normalized_target == "OUT_FOR_DELIVERY":
        if order.rider_id is not None:
            rider = db.query(Rider).filter(Rider.id == order.rider_id).first()
            if rider:
                rider.status = "DELIVERING"
    elif normalized_target == "DELIVERED":
        release_reserved_on_delivery(db, order)
        if order.rider_id is not None:
            rider = db.query(Rider).filter(Rider.id == order.rider_id).first()
            if rider:
                rider.status = "IDLE"

    event = OrderEvent(
        order_id=order.id,
        from_status=previous_status,
        to_status=normalized_target,
        note=note or f"Status updated from {previous_status} to {normalized_target}",
    )
    db.add(event)
    db.commit()
    db.refresh(order)
    return order
