from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    lat: float
    lng: float
    active_pickers: int


class InventoryItemOut(BaseModel):
    id: int
    store_id: int
    product_id: int
    sku: str
    name: str
    category: str
    aisle_code: str
    price_inr: float
    stock_available: int
    stock_reserved: int
    reorder_threshold: int
    image_url: Optional[str] = None


class RiderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    name: str
    status: str
    current_lat: float
    current_lng: float


class OrderItemIn(BaseModel):
    product_id: int
    quantity: int = Field(..., ge=1, le=50)


class OrderCreateIn(BaseModel):
    store_id: int
    customer_name: str = Field(..., min_length=1, max_length=120)
    delivery_lat: float
    delivery_lng: float
    items: List[OrderItemIn] = Field(..., min_length=1)


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    sku: str
    name: str
    category: str
    aisle_code: str
    quantity: int
    unit_price_inr: float


class OrderEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    from_status: Optional[str] = None
    to_status: str
    timestamp: datetime
    note: Optional[str] = None


class OrderOut(BaseModel):
    id: int
    store_id: int
    store_name: str
    customer_name: str
    delivery_lat: float
    delivery_lng: float
    status: str
    created_at: datetime
    predicted_eta_sec: int
    sla_risk_score: float
    rider_id: Optional[int] = None
    rider_name: Optional[str] = None
    total_inr: float
    items: List[OrderItemOut]
    events: List[OrderEventOut]


class OrderStatusUpdateIn(BaseModel):
    status: str
    note: Optional[str] = None


class RestockIn(BaseModel):
    quantity: int = Field(default=10, ge=1, le=500)


class SimulationTriggerIn(BaseModel):
    store_id: Optional[int] = None
