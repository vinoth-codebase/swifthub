from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import Base, SessionLocal, engine, get_db
from app.models import Order, OrderItem, Rider, Store, StoreInventory
from app.schemas import InventoryItemOut, OrderItemOut, OrderOut, RiderOut, StoreOut
from app.seed import seed_database


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
        customer_name=order.customer_name,
        delivery_lat=order.delivery_lat,
        delivery_lng=order.delivery_lng,
        status=order.status,
        created_at=order.created_at,
        predicted_eta_sec=order.predicted_eta_sec,
        sla_risk_score=order.sla_risk_score,
        rider_id=order.rider_id,
        rider_name=order.rider.name if order.rider else None,
        total_inr=total_inr,
        items=items_out,
        events=order.events,
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="SwiftHub Dark-Store & 10-Minute Dispatch API",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [o.strip() for o in settings.FRONTEND_URL.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "swifthub-backend"}


@app.get("/api/stores", response_model=List[StoreOut])
def list_stores(db: Session = Depends(get_db)):
    return db.query(Store).order_by(Store.id.asc()).all()


@app.get("/api/stores/{store_id}/inventory", response_model=List[InventoryItemOut])
def list_store_inventory(
    store_id: int,
    category: Optional[str] = None,
    q: Optional[str] = None,
    low_stock_only: bool = False,
    db: Session = Depends(get_db),
):
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    query = (
        db.query(StoreInventory)
        .options(joinedload(StoreInventory.product))
        .filter(StoreInventory.store_id == store_id)
    )
    items = query.all()
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


@app.get("/api/riders", response_model=List[RiderOut])
def list_riders(store_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Rider)
    if store_id is not None:
        query = query.filter(Rider.store_id == store_id)
    return query.order_by(Rider.id.asc()).all()


@app.get("/api/orders", response_model=List[OrderOut])
def list_orders(
    store_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = (
        db.query(Order)
        .options(
            joinedload(Order.store),
            joinedload(Order.rider),
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.events),
        )
    )
    if store_id is not None:
        query = query.filter(Order.store_id == store_id)
    if status:
        query = query.filter(Order.status == status.upper())
    orders = query.order_by(Order.created_at.desc()).all()
    return [serialize_order(o) for o in orders]
