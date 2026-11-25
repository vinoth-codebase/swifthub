from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), unique=True, nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    active_pickers = Column(Integer, nullable=False, default=4)

    inventory = relationship("StoreInventory", back_populates="store", cascade="all, delete-orphan")
    riders = relationship("Rider", back_populates="store", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="store")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(160), nullable=False)
    category = Column(String(80), nullable=False, index=True)
    aisle_code = Column(String(40), nullable=False)
    price_inr = Column(Float, nullable=False)
    image_url = Column(String(500), nullable=True)

    store_inventories = relationship("StoreInventory", back_populates="product")


class StoreInventory(Base):
    __tablename__ = "store_inventory"
    __table_args__ = (UniqueConstraint("store_id", "product_id", name="uq_store_product"),)

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    stock_available = Column(Integer, nullable=False, default=0)
    stock_reserved = Column(Integer, nullable=False, default=0)
    reorder_threshold = Column(Integer, nullable=False, default=5)

    store = relationship("Store", back_populates="inventory")
    product = relationship("Product", back_populates="store_inventories")


class Rider(Base):
    __tablename__ = "riders"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    status = Column(String(32), nullable=False, default="IDLE", index=True)
    current_lat = Column(Float, nullable=False)
    current_lng = Column(Float, nullable=False)

    store = relationship("Store", back_populates="riders")
    orders = relationship("Order", back_populates="rider")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(120), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="CUSTOMER", index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    store = relationship("Store")
    orders = relationship("Order", back_populates="customer")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    customer_name = Column(String(120), nullable=False)
    delivery_lat = Column(Float, nullable=False)
    delivery_lng = Column(Float, nullable=False)
    status = Column(String(32), nullable=False, default="PLACED", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    predicted_eta_sec = Column(Integer, nullable=False, default=420)
    sla_risk_score = Column(Float, nullable=False, default=0.15)
    rider_id = Column(Integer, ForeignKey("riders.id"), nullable=True, index=True)

    store = relationship("Store", back_populates="orders")
    customer = relationship("User", back_populates="orders")
    rider = relationship("Rider", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    events = relationship(
        "OrderEvent",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderEvent.timestamp.asc()",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price_inr = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")


class OrderEvent(Base):
    __tablename__ = "order_events"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status = Column(String(32), nullable=True)
    to_status = Column(String(32), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    note = Column(String(255), nullable=True)

    order = relationship("Order", back_populates="events")
