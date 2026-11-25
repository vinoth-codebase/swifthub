import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload

from app.auth import (
    ROLE_BRANCH_ADMIN,
    ROLE_CUSTOMER,
    create_access_token,
    get_current_user,
    get_optional_user,
    hash_password,
    require_branch_admin,
    require_customer,
    verify_password,
)
from app.config import settings
from app.database import Base, SessionLocal, engine, get_db
from app.models import Order, OrderEvent, OrderItem, Rider, Store, StoreInventory, User
from app.schemas import (
    AuthTokenOut,
    InventoryItemOut,
    LoginIn,
    OrderCreateIn,
    OrderItemOut,
    OrderOut,
    OrderStatusUpdateIn,
    RegisterIn,
    RestockIn,
    RiderOut,
    SimulationTriggerIn,
    StoreOut,
    UserOut,
)
from app.seed import seed_database
from app.services.inventory import (
    aggregate_items,
    reserve_inventory_atomic,
    restock_inventory_atomic,
)
from app.services.ml_inference import haversine_km, sla_predictor
from app.services.simulator import create_simulated_order, run_order_lifecycle_simulation
from app.services.state_machine import transition_order_status
from app.ws import ws_manager


def serialize_user(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        store_id=user.store_id,
        store_name=user.store.name if user.store else None,
    )


def serialize_inventory(inv: StoreInventory) -> InventoryItemOut:
    return InventoryItemOut(
        id=inv.id,
        store_id=inv.store_id,
        product_id=inv.product_id,
        sku=inv.product.sku,
        name=inv.product.name,
        category=inv.product.category,
        aisle_code=inv.product.aisle_code,
        price_inr=inv.product.price_inr,
        stock_available=inv.stock_available,
        stock_reserved=inv.stock_reserved,
        reorder_threshold=inv.reorder_threshold,
        image_url=inv.product.image_url,
    )


def serialize_order(order: Order) -> OrderOut:
    items_out = [
        OrderItemOut(
            id=item.id,
            product_id=item.product_id,
            sku=item.product.sku,
            name=item.product.name,
            category=item.product.category,
            aisle_code=item.product.aisle_code,
            quantity=item.quantity,
            unit_price_inr=item.unit_price_inr,
        )
        for item in sorted(order.items, key=lambda it: it.product.aisle_code)
    ]
    total_inr = round(sum(it.quantity * it.unit_price_inr for it in items_out), 2)
    return OrderOut(
        id=order.id,
        store_id=order.store_id,
        store_name=order.store.name if order.store else "",
        customer_id=order.customer_id,
        customer_name=order.customer_name,
        delivery_lat=order.delivery_lat,
        delivery_lng=order.delivery_lng,
        status=order.status,
        created_at=order.created_at,
        predicted_eta_sec=order.predicted_eta_sec,
        sla_risk_score=order.sla_risk_score,
        rider_id=order.rider_id,
        rider_name=order.rider.name if order.rider else None,
        rider_status=order.rider.status if order.rider else None,
        rider_lat=order.rider.current_lat if order.rider else None,
        rider_lng=order.rider.current_lng if order.rider else None,
        total_inr=total_inr,
        items=items_out,
        events=order.events,
    )


def _load_order(db: Session, order_id: int) -> Optional[Order]:
    return (
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


def _assert_admin_store_access(admin: User, store_id: int) -> None:
    if admin.store_id != store_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you are restricted to your assigned dark-store branch.",
        )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    sla_predictor.load()
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="SwiftHub Dark-Store & 10-Minute Dispatch API",
    version="2.0.0",
    lifespan=lifespan,
)

origins = [o.strip().rstrip("/") for o in settings.FRONTEND_URL.split(",") if o.strip()]
default_dev_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
allowed_origins = list(dict.fromkeys(origins + default_dev_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "swifthub-backend",
        "ml_loaded": sla_predictor.eta_model is not None,
    }


@app.get("/api/ml/metrics")
def get_ml_metrics():
    return {
        "loaded": sla_predictor.eta_model is not None and sla_predictor.sla_model is not None,
        "metrics": sla_predictor.metrics,
    }


# ---------------------------------------------------------------------------
# Authentication Routes
# ---------------------------------------------------------------------------

@app.post("/api/auth/register", response_model=AuthTokenOut, status_code=201)
def register_customer(payload: RegisterIn, db: Session = Depends(get_db)):
    normalized_email = payload.email.strip().lower()
    if "@" not in normalized_email or "." not in normalized_email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = User(
        email=normalized_email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=ROLE_CUSTOMER,
        store_id=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user)
    return AuthTokenOut(access_token=token, user=serialize_user(user))


@app.post("/api/auth/login", response_model=AuthTokenOut)
def login_user(payload: LoginIn, db: Session = Depends(get_db)):
    normalized_email = payload.email.strip().lower()
    user = (
        db.query(User)
        .options(joinedload(User.store))
        .filter(User.email == normalized_email)
        .first()
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token(user)
    return AuthTokenOut(access_token=token, user=serialize_user(user))


@app.get("/api/auth/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return serialize_user(current_user)


# ---------------------------------------------------------------------------
# Public Storefront & Branch-Isolated Inventory Routes
# ---------------------------------------------------------------------------

@app.get("/api/stores", response_model=List[StoreOut])
def list_stores(db: Session = Depends(get_db)):
    return db.query(Store).order_by(Store.id.asc()).all()


@app.get("/api/stores/{store_id}/inventory", response_model=List[InventoryItemOut])
def list_store_inventory(
    store_id: int,
    category: Optional[str] = None,
    q: Optional[str] = None,
    low_stock_only: bool = False,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    if current_user is not None and current_user.role == ROLE_BRANCH_ADMIN:
        _assert_admin_store_access(current_user, store_id)

    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    items = (
        db.query(StoreInventory)
        .options(joinedload(StoreInventory.product))
        .filter(StoreInventory.store_id == store_id)
        .all()
    )
    results = []
    for inv in items:
        if category and category.lower() != "all" and inv.product.category.lower() != category.lower():
            continue
        if q:
            term = q.lower()
            if (
                term not in inv.product.name.lower()
                and term not in inv.product.sku.lower()
                and term not in inv.product.aisle_code.lower()
            ):
                continue
        if low_stock_only and inv.stock_available > inv.reorder_threshold:
            continue
        results.append(serialize_inventory(inv))

    results.sort(key=lambda x: (x.aisle_code, x.name))
    return results


@app.post("/api/stores/{store_id}/inventory/{product_id}/restock", response_model=InventoryItemOut)
async def restock_inventory(
    store_id: int,
    product_id: int,
    payload: RestockIn,
    current_user: User = Depends(require_branch_admin),
    db: Session = Depends(get_db),
):
    _assert_admin_store_access(current_user, store_id)
    inv = restock_inventory_atomic(db, store_id, product_id, payload.quantity)
    inv_loaded = (
        db.query(StoreInventory)
        .options(joinedload(StoreInventory.product))
        .filter(StoreInventory.id == inv.id)
        .first()
    )
    inv_out = serialize_inventory(inv_loaded)
    await ws_manager.broadcast(
        "INVENTORY_UPDATED",
        {"store_id": store_id, "item": inv_out.model_dump(mode="json")},
    )
    return inv_out


# ---------------------------------------------------------------------------
# Branch-Isolated Rider Dispatch Routes (Admin Only)
# ---------------------------------------------------------------------------

@app.get("/api/riders", response_model=List[RiderOut])
def list_riders(
    store_id: Optional[int] = None,
    current_user: User = Depends(require_branch_admin),
    db: Session = Depends(get_db),
):
    if store_id is not None:
        _assert_admin_store_access(current_user, store_id)
    return (
        db.query(Rider)
        .filter(Rider.store_id == current_user.store_id)
        .order_by(Rider.id.asc())
        .all()
    )


# ---------------------------------------------------------------------------
# Orders Routes (Role-Scoped & Branch-Isolated)
# ---------------------------------------------------------------------------

@app.get("/api/orders", response_model=List[OrderOut])
def list_orders(
    store_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Order).options(
        joinedload(Order.store),
        joinedload(Order.rider),
        joinedload(Order.items).joinedload(OrderItem.product),
        joinedload(Order.events),
    )

    if current_user.role == ROLE_BRANCH_ADMIN:
        if store_id is not None:
            _assert_admin_store_access(current_user, store_id)
        query = query.filter(Order.store_id == current_user.store_id)
    else:
        query = query.filter(Order.customer_id == current_user.id)
        if store_id is not None:
            query = query.filter(Order.store_id == store_id)

    if status_filter:
        query = query.filter(Order.status == status_filter.upper())

    orders = query.order_by(Order.created_at.desc()).all()
    return [serialize_order(o) for o in orders]


@app.get("/api/orders/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = _load_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if current_user.role == ROLE_BRANCH_ADMIN:
        _assert_admin_store_access(current_user, order.store_id)
    elif order.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you can only view your own orders.",
        )

    return serialize_order(order)


@app.post("/api/orders", response_model=OrderOut, status_code=201)
async def create_order(
    payload: OrderCreateIn,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    store = db.query(Store).filter(Store.id == payload.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    raw_items = [(it.product_id, it.quantity) for it in payload.items]
    ordered_items = aggregate_items(raw_items)

    products_map = reserve_inventory_atomic(db, payload.store_id, ordered_items)

    item_count = sum(qty for _, qty in ordered_items)
    unique_aisles = len({products_map[pid].aisle_code for pid, _ in ordered_items})
    active_queue_depth = (
        db.query(Order)
        .filter(
            Order.store_id == payload.store_id,
            Order.status.in_(["PLACED", "PICKING", "PACKED"]),
        )
        .count()
    )
    idle_riders = (
        db.query(Rider)
        .filter(Rider.store_id == payload.store_id, Rider.status == "IDLE")
        .count()
    )
    distance_km = haversine_km(
        store.lat, store.lng, payload.delivery_lat, payload.delivery_lng
    )
    predicted_eta_sec, sla_risk_score = sla_predictor.predict(
        item_count=item_count,
        unique_aisles=unique_aisles,
        active_queue_depth=active_queue_depth,
        idle_riders=idle_riders,
        distance_km=distance_km,
    )

    order = Order(
        store_id=payload.store_id,
        customer_id=current_user.id,
        customer_name=payload.customer_name.strip(),
        delivery_lat=payload.delivery_lat,
        delivery_lng=payload.delivery_lng,
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
            note="Order placed and inventory reserved",
        )
    )
    db.commit()

    loaded = _load_order(db, order.id)
    order_out = serialize_order(loaded)
    await ws_manager.broadcast("ORDER_CREATED", order_out.model_dump(mode="json"))
    await ws_manager.broadcast("INVENTORY_UPDATED", {"store_id": payload.store_id})
    return order_out


@app.post("/api/orders/{order_id}/cancel", response_model=OrderOut)
async def cancel_customer_order(
    order_id: int,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you can only cancel your own orders.",
        )

    transition_order_status(db, order_id, "CANCELLED", "Cancelled by customer prior to dispatch")
    loaded = _load_order(db, order_id)
    order_out = serialize_order(loaded)
    await ws_manager.broadcast("ORDER_UPDATED", order_out.model_dump(mode="json"))
    await ws_manager.broadcast("INVENTORY_UPDATED", {"store_id": order_out.store_id})
    riders = db.query(Rider).filter(Rider.store_id == order_out.store_id).all()
    await ws_manager.broadcast(
        "RIDERS_UPDATED",
        {
            "store_id": order_out.store_id,
            "riders": [RiderOut.model_validate(r).model_dump(mode="json") for r in riders],
        },
    )
    return order_out


@app.patch("/api/orders/{order_id}/status", response_model=OrderOut)
async def update_order_status(
    order_id: int,
    payload: OrderStatusUpdateIn,
    current_user: User = Depends(require_branch_admin),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    _assert_admin_store_access(current_user, order.store_id)

    transition_order_status(db, order_id, payload.status, payload.note)
    loaded = _load_order(db, order_id)
    order_out = serialize_order(loaded)
    await ws_manager.broadcast("ORDER_UPDATED", order_out.model_dump(mode="json"))
    if order_out.rider_id is not None or order_out.status in {
        "PACKED",
        "OUT_FOR_DELIVERY",
        "DELIVERED",
        "CANCELLED",
    }:
        riders = db.query(Rider).filter(Rider.store_id == order_out.store_id).all()
        await ws_manager.broadcast(
            "RIDERS_UPDATED",
            {
                "store_id": order_out.store_id,
                "riders": [RiderOut.model_validate(r).model_dump(mode="json") for r in riders],
            },
        )
    if order_out.status == "CANCELLED":
        await ws_manager.broadcast("INVENTORY_UPDATED", {"store_id": order_out.store_id})
    return order_out


# ---------------------------------------------------------------------------
# Live Demo Simulation & Operations Analytics (Admin Only, Branch-Isolated)
# ---------------------------------------------------------------------------

@app.post("/api/simulation/trigger", response_model=OrderOut, status_code=201)
async def trigger_simulation(
    payload: Optional[SimulationTriggerIn] = None,
    current_user: User = Depends(require_branch_admin),
    db: Session = Depends(get_db),
):
    if payload and payload.store_id is not None:
        _assert_admin_store_access(current_user, payload.store_id)

    target_store_id = current_user.store_id
    try:
        order = create_simulated_order(db, store_id=target_store_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    loaded = _load_order(db, order.id)
    order_out = serialize_order(loaded)
    await ws_manager.broadcast("ORDER_CREATED", order_out.model_dump(mode="json"))
    await ws_manager.broadcast("INVENTORY_UPDATED", {"store_id": order_out.store_id})

    asyncio.create_task(
        run_order_lifecycle_simulation(
            order.id,
            lambda o: serialize_order(o).model_dump(mode="json"),
        )
    )
    return order_out


@app.get("/api/analytics")
def get_analytics(
    store_id: Optional[int] = None,
    current_user: User = Depends(require_branch_admin),
    db: Session = Depends(get_db),
):
    if store_id is not None:
        _assert_admin_store_access(current_user, store_id)

    orders = (
        db.query(Order)
        .options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.events),
        )
        .filter(Order.store_id == current_user.store_id)
        .all()
    )

    total_orders = len(orders)
    delivered_orders = [o for o in orders if o.status == "DELIVERED"]
    cancelled_orders = [o for o in orders if o.status == "CANCELLED"]
    active_orders = [o for o in orders if o.status not in {"DELIVERED", "CANCELLED"}]

    sla_met = 0
    pick_durations = []
    pack_durations = []
    delivery_durations = []
    total_durations = []
    category_counts: dict[str, int] = {}

    for o in orders:
        for item in o.items:
            cat = item.product.category
            category_counts[cat] = category_counts.get(cat, 0) + item.quantity

        event_times = {}
        for ev in o.events:
            if ev.to_status not in event_times:
                event_times[ev.to_status] = ev.timestamp

        if "PICKING" in event_times and "PACKED" in event_times:
            pick_sec = (event_times["PACKED"] - event_times["PICKING"]).total_seconds()
            if pick_sec >= 0:
                pick_durations.append(pick_sec)
        if "PACKED" in event_times and "OUT_FOR_DELIVERY" in event_times:
            pack_sec = (event_times["OUT_FOR_DELIVERY"] - event_times["PACKED"]).total_seconds()
            if pack_sec >= 0:
                pack_durations.append(pack_sec)
        if "OUT_FOR_DELIVERY" in event_times and "DELIVERED" in event_times:
            del_sec = (event_times["DELIVERED"] - event_times["OUT_FOR_DELIVERY"]).total_seconds()
            if del_sec >= 0:
                delivery_durations.append(del_sec)
        if "PLACED" in event_times and "DELIVERED" in event_times:
            tot_sec = (event_times["DELIVERED"] - event_times["PLACED"]).total_seconds()
            if tot_sec >= 0:
                total_durations.append(tot_sec)
                if tot_sec <= 600:
                    sla_met += 1

    delivered_count = len(delivered_orders)
    sla_compliance_pct = (
        round((sla_met / len(total_durations)) * 100, 1) if total_durations else 100.0
    )

    return {
        "total_orders": total_orders,
        "active_orders": len(active_orders),
        "delivered_orders": delivered_count,
        "cancelled_orders": len(cancelled_orders),
        "sla_compliance_pct": sla_compliance_pct,
        "sla_met_count": sla_met,
        "sla_breached_count": max(0, len(total_durations) - sla_met),
        "avg_pick_time_sec": round(sum(pick_durations) / len(pick_durations), 1) if pick_durations else 0.0,
        "avg_dispatch_wait_sec": round(sum(pack_durations) / len(pack_durations), 1) if pack_durations else 0.0,
        "avg_delivery_time_sec": round(sum(delivery_durations) / len(delivery_durations), 1) if delivery_durations else 0.0,
        "avg_total_fulfillment_sec": round(sum(total_durations) / len(total_durations), 1) if total_durations else 0.0,
        "category_volume": [
            {"category": k, "units": v}
            for k, v in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        ],
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
