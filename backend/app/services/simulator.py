import asyncio
import math
import random
from typing import Callable, Optional

from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models import Order, OrderEvent, OrderItem, Rider, Store, StoreInventory
from app.schemas import RiderOut
from app.services.inventory import aggregate_items, reserve_inventory_atomic
from app.services.ml_inference import haversine_km, sla_predictor
from app.services.state_machine import transition_order_status
from app.ws import ws_manager

DEMO_CUSTOMERS = [
    "Aarav Sharma",
    "Diya Nair",
    "Ishaan Rao",
    "Tanvi Kulkarni",
    "Kabir Mehta",
    "Sneha Reddy",
]


async def run_order_lifecycle_simulation(
    order_id: int,
    serialize_order_fn: Callable[[Order], dict],
) -> None:
    """
    Animate a simulated order through PLACED -> PICKING -> PACKED -> OUT_FOR_DELIVERY -> DELIVERED
    with smooth rider GPS updates over ~35 seconds.
    """
    try:
        # Phase 1: Start Picking (~4s)
        await asyncio.sleep(4.0)
        if not await _advance_step(order_id, "PICKING", "Picker started aisle sweep (Demo)", serialize_order_fn):
            return

        # Phase 2: Mark Packed + Auto-Assign Nearest Rider (~6s)
        await asyncio.sleep(6.0)
        if not await _advance_step(order_id, "PACKED", "Order packed and sealed (Demo)", serialize_order_fn):
            return

        # Phase 3: Dispatch Rider (~3s)
        await asyncio.sleep(3.0)
        if not await _advance_step(order_id, "OUT_FOR_DELIVERY", "Rider departed dark-store hub (Demo)", serialize_order_fn):
            return

        # Phase 4: Animate Rider GPS from hub to customer over 10 steps (~20s)
        steps = 10
        for step in range(1, steps + 1):
            await asyncio.sleep(2.0)
            db = SessionLocal()
            try:
                order = (
                    db.query(Order)
                    .options(joinedload(Order.store), joinedload(Order.rider))
                    .filter(Order.id == order_id)
                    .first()
                )
                if not order or order.status != "OUT_FOR_DELIVERY" or not order.rider:
                    return

                progress = step / steps
                # Slight smooth lateral offset for realistic road curvature
                curve = math.sin(progress * math.pi) * 0.0008
                new_lat = order.store.lat + (order.delivery_lat - order.store.lat) * progress + curve
                new_lng = order.store.lng + (order.delivery_lng - order.store.lng) * progress - curve * 0.6

                order.rider.current_lat = round(new_lat, 6)
                order.rider.current_lng = round(new_lng, 6)
                db.commit()

                rider_data = RiderOut.model_validate(order.rider).model_dump(mode="json")
                await ws_manager.broadcast(
                    "RIDER_LOCATION",
                    {
                        "order_id": order.id,
                        "store_id": order.store_id,
                        "rider": rider_data,
                        "progress": round(progress, 2),
                    },
                )
            finally:
                db.close()

        # Phase 5: Mark Delivered (~2s)
        await asyncio.sleep(2.0)
        await _advance_step(order_id, "DELIVERED", "Order delivered at customer doorstep (Demo)", serialize_order_fn)
    except Exception:
        return


async def _advance_step(
    order_id: int,
    target_status: str,
    note: str,
    serialize_order_fn: Callable[[Order], dict],
) -> bool:
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order or order.status in {"CANCELLED", "DELIVERED"}:
            return False

        transition_order_status(db, order_id, target_status, note)

        loaded = (
            db.query(Order)
            .options(
                joinedload(Order.store),
                joinedload(Order.rider),
                joinedload(Order.items).joinedload(OrderItem.product),
                joinedload(Order.events),
            )
            .filter(Order.id == order_id)
            .first()
        )
        if not loaded:
            return False

        # Snap rider to hub when starting delivery so animation begins cleanly at dark store
        if target_status == "OUT_FOR_DELIVERY" and loaded.rider:
            loaded.rider.current_lat = loaded.store.lat
            loaded.rider.current_lng = loaded.store.lng
            db.commit()

        await ws_manager.broadcast("ORDER_UPDATED", serialize_order_fn(loaded))

        riders = db.query(Rider).filter(Rider.store_id == loaded.store_id).all()
        await ws_manager.broadcast(
            "RIDERS_UPDATED",
            {
                "store_id": loaded.store_id,
                "riders": [RiderOut.model_validate(r).model_dump(mode="json") for r in riders],
            },
        )
        return True
    finally:
        db.close()


def create_simulated_order(db: Session, store_id: Optional[int] = None) -> Order:
    if store_id is not None:
        store = db.query(Store).filter(Store.id == store_id).first()
    else:
        store = db.query(Store).order_by(Store.id.asc()).first()

    if not store:
        raise ValueError("No dark-store hub available for simulation")

    in_stock = (
        db.query(StoreInventory)
        .options(joinedload(StoreInventory.product))
        .filter(StoreInventory.store_id == store.id, StoreInventory.stock_available >= 1)
        .all()
    )
    if not in_stock:
        # Auto-replenish first two SKUs if demo store is depleted
        all_inv = (
            db.query(StoreInventory)
            .options(joinedload(StoreInventory.product))
            .filter(StoreInventory.store_id == store.id)
            .limit(3)
            .all()
        )
        for inv in all_inv:
            inv.stock_available += 5
        db.commit()
        in_stock = all_inv

    sample_count = min(len(in_stock), random.randint(2, 4))
    chosen = random.sample(in_stock, sample_count)
    ordered_items = aggregate_items([(inv.product_id, 1) for inv in chosen])

    products_map = reserve_inventory_atomic(db, store.id, ordered_items)

    # Generate realistic Bangalore drop-off coordinate 0.7 - 2.1 km away from hub
    angle = random.uniform(0, 2 * math.pi)
    radius_deg = random.uniform(0.007, 0.017)
    delivery_lat = round(store.lat + math.cos(angle) * radius_deg, 6)
    delivery_lng = round(store.lng + math.sin(angle) * radius_deg, 6)

    item_count = sum(qty for _, qty in ordered_items)
    unique_aisles = len({products_map[pid].aisle_code for pid, _ in ordered_items})
    active_queue_depth = (
        db.query(Order)
        .filter(
            Order.store_id == store.id,
            Order.status.in_(["PLACED", "PICKING", "PACKED"]),
        )
        .count()
    )
    idle_riders = (
        db.query(Rider)
        .filter(Rider.store_id == store.id, Rider.status == "IDLE")
        .count()
    )
    distance_km = haversine_km(store.lat, store.lng, delivery_lat, delivery_lng)
    predicted_eta_sec, sla_risk_score = sla_predictor.predict(
        item_count=item_count,
        unique_aisles=unique_aisles,
        active_queue_depth=active_queue_depth,
        idle_riders=idle_riders,
        distance_km=distance_km,
    )

    order = Order(
        store_id=store.id,
        customer_name=f"{random.choice(DEMO_CUSTOMERS)} (Live Demo)",
        delivery_lat=delivery_lat,
        delivery_lng=delivery_lng,
        status="PLACED",
        predicted_eta_sec=predicted_eta_sec,
        sla_risk_score=sla_risk_score,
    )
    db.add(order)
    db.flush()

    for product_id, qty in ordered_items:
        product = products_map[product_id]
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product_id,
                quantity=qty,
                unit_price_inr=product.price_inr,
            )
        )

    db.add(
        OrderEvent(
            order_id=order.id,
            from_status=None,
            to_status="PLACED",
            note="Live demo simulation order created",
        )
    )
    db.commit()
    return order
