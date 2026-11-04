from typing import Dict, List, Tuple
from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import Order, Product, StoreInventory


def aggregate_items(items: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Aggregate duplicate product_ids and sort deterministically to avoid lock-order deadlocks."""
    totals: Dict[int, int] = {}
    for product_id, qty in items:
        totals[product_id] = totals.get(product_id, 0) + qty
    return sorted(totals.items(), key=lambda pair: pair[0])


def reserve_inventory_atomic(
    db: Session, store_id: int, items: List[Tuple[int, int]]
) -> Dict[int, Product]:
    """
    Atomically decrement stock_available and increment stock_reserved using conditional UPDATE
    (WHERE stock_available >= qty). Rolls back and raises HTTP 409 Conflict if any SKU lacks stock.
    """
    ordered_items = aggregate_items(items)
    products_map: Dict[int, Product] = {}

    for product_id, qty in ordered_items:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Product ID {product_id} not found")
        products_map[product_id] = product

        stmt = (
            update(StoreInventory)
            .where(
                StoreInventory.store_id == store_id,
                StoreInventory.product_id == product_id,
                StoreInventory.stock_available >= qty,
            )
            .values(
                stock_available=StoreInventory.stock_available - qty,
                stock_reserved=StoreInventory.stock_reserved + qty,
            )
        )
        result = db.execute(stmt)
        if result.rowcount != 1:
            current = (
                db.query(StoreInventory)
                .filter(
                    StoreInventory.store_id == store_id,
                    StoreInventory.product_id == product_id,
                )
                .first()
            )
            avail = current.stock_available if current else 0
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Insufficient stock for {product.name} ({product.sku}): "
                    f"requested {qty}, available {avail}."
                ),
            )

    return products_map


def release_reserved_on_delivery(db: Session, order: Order) -> None:
    """Decrement stock_reserved once an order is delivered."""
    for item in order.items:
        stmt = (
            update(StoreInventory)
            .where(
                StoreInventory.store_id == order.store_id,
                StoreInventory.product_id == item.product_id,
                StoreInventory.stock_reserved >= item.quantity,
            )
            .values(stock_reserved=StoreInventory.stock_reserved - item.quantity)
        )
        db.execute(stmt)


def restore_inventory_atomic(db: Session, order: Order) -> None:
    """Atomically restore stock_available when an order is cancelled prior to dispatch."""
    for item in sorted(order.items, key=lambda it: it.product_id):
        inv = (
            db.query(StoreInventory)
            .filter(
                StoreInventory.store_id == order.store_id,
                StoreInventory.product_id == item.product_id,
            )
            .first()
        )
        if not inv:
            continue
        reserved_deduction = min(inv.stock_reserved, item.quantity)
        stmt = (
            update(StoreInventory)
            .where(
                StoreInventory.store_id == order.store_id,
                StoreInventory.product_id == item.product_id,
            )
            .values(
                stock_available=StoreInventory.stock_available + item.quantity,
                stock_reserved=StoreInventory.stock_reserved - reserved_deduction,
            )
        )
        db.execute(stmt)


def restock_inventory_atomic(
    db: Session, store_id: int, product_id: int, quantity: int
) -> StoreInventory:
    stmt = (
        update(StoreInventory)
        .where(
            StoreInventory.store_id == store_id,
            StoreInventory.product_id == product_id,
        )
        .values(stock_available=StoreInventory.stock_available + quantity)
    )
    result = db.execute(stmt)
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=404, detail="Inventory item not found for this store")
    db.commit()
    inv = (
        db.query(StoreInventory)
        .filter(
            StoreInventory.store_id == store_id,
            StoreInventory.product_id == product_id,
        )
        .first()
    )
    return inv
