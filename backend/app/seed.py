from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import Order, OrderEvent, OrderItem, Product, Rider, Store, StoreInventory


STORES_DATA = [
    {"name": "Koramangala Hub", "lat": 12.9352, "lng": 77.6245, "active_pickers": 6},
    {"name": "Indiranagar Hub", "lat": 12.9784, "lng": 77.6408, "active_pickers": 5},
    {"name": "HSR Layout Hub", "lat": 12.9116, "lng": 77.6389, "active_pickers": 4},
]

PRODUCTS_DATA = [
    {"sku": "DAI-001", "name": "Nandini GoodLife Toned Milk 500ml", "category": "Dairy", "aisle_code": "A1-Dairy", "price_inr": 32.0},
    {"sku": "DAI-002", "name": "Amul Malai Paneer 200g", "category": "Dairy", "aisle_code": "A1-Dairy", "price_inr": 95.0},
    {"sku": "DAI-003", "name": "Epigamia Greek Yogurt Natural 90g", "category": "Dairy", "aisle_code": "A1-Dairy", "price_inr": 65.0},
    {"sku": "BAK-001", "name": "Britannia Whole Wheat Bread 400g", "category": "Bakery", "aisle_code": "A2-Bakery", "price_inr": 55.0},
    {"sku": "BAK-002", "name": "Artisan Sourdough Loaf 350g", "category": "Bakery", "aisle_code": "A2-Bakery", "price_inr": 145.0},
    {"sku": "BAK-003", "name": "Butter Croissant Pack of 2", "category": "Bakery", "aisle_code": "A2-Bakery", "price_inr": 110.0},
    {"sku": "PRO-001", "name": "Farm Fresh Robusta Bananas 500g", "category": "Produce", "aisle_code": "A3-Produce", "price_inr": 42.0},
    {"sku": "PRO-002", "name": "Organic Cherry Tomatoes 250g", "category": "Produce", "aisle_code": "A3-Produce", "price_inr": 78.0},
    {"sku": "PRO-003", "name": "Hass Avocado Single Piece", "category": "Produce", "aisle_code": "A3-Produce", "price_inr": 165.0},
    {"sku": "PRO-004", "name": "Baby Spinach Washed 200g", "category": "Produce", "aisle_code": "A3-Produce", "price_inr": 60.0},
    {"sku": "SNK-001", "name": "Kettle Studio Sea Salt Chips 113g", "category": "Snacks", "aisle_code": "A4-Snacks", "price_inr": 99.0},
    {"sku": "SNK-002", "name": "Roasted Makhana Peri Peri 60g", "category": "Snacks", "aisle_code": "A4-Snacks", "price_inr": 120.0},
    {"sku": "SNK-003", "name": "Dark Chocolate 70% Bar 100g", "category": "Snacks", "aisle_code": "A4-Snacks", "price_inr": 180.0},
    {"sku": "BEV-001", "name": "Cold Brew Coffee Classic 250ml", "category": "Beverages", "aisle_code": "A5-Beverages", "price_inr": 115.0},
    {"sku": "BEV-002", "name": "Raw Pressery Valencia Orange 200ml", "category": "Beverages", "aisle_code": "A5-Beverages", "price_inr": 85.0},
    {"sku": "BEV-003", "name": "Tender Coconut Water 200ml", "category": "Beverages", "aisle_code": "A5-Beverages", "price_inr": 50.0},
    {"sku": "PAN-001", "name": "ID Fresh Idli Dosa Batter 1kg", "category": "Pantry", "aisle_code": "A6-Pantry", "price_inr": 92.0},
    {"sku": "PAN-002", "name": "Cold Pressed Groundnut Oil 1L", "category": "Pantry", "aisle_code": "A6-Pantry", "price_inr": 340.0},
]

# Initial stock quantities per SKU index so every store has healthy stock plus realistic low-stock SKUs
DEFAULT_STOCKS = [18, 4, 12, 15, 2, 9, 22, 3, 1, 14, 20, 5, 11, 2, 16, 19, 4, 8]

RIDERS_BY_STORE = {
    "Koramangala Hub": [
        ("Arjun Rao", 0.0020, -0.0015),
        ("Karthik Nair", -0.0018, 0.0022),
        ("Deepak Gowda", 0.0012, 0.0018),
        ("Suresh Babu", -0.0025, -0.0010),
    ],
    "Indiranagar Hub": [
        ("Vikram Shetty", 0.0015, 0.0020),
        ("Manoj Kumar", -0.0021, 0.0011),
        ("Praveen Hegde", 0.0009, -0.0024),
        ("Rohan Das", -0.0014, -0.0019),
    ],
    "HSR Layout Hub": [
        ("Nikhil Verma", 0.0022, 0.0012),
        ("Santosh Reddy", -0.0016, 0.0025),
        ("Harish Murthy", 0.0011, -0.0017),
        ("Ajay Kulkarni", -0.0020, -0.0013),
    ],
}


def seed_database(db: Session) -> bool:
    """Seed stores, products, inventory, riders, and baseline operational history if DB is empty."""
    if db.query(Store).count() > 0:
        return False

    stores: list[Store] = []
    for s_data in STORES_DATA:
        store = Store(**s_data)
        db.add(store)
        stores.append(store)
    db.flush()

    products: list[Product] = []
    for p_data in PRODUCTS_DATA:
        product = Product(**p_data)
        db.add(product)
        products.append(product)
    db.flush()

    for store_idx, store in enumerate(stores):
        for prod_idx, product in enumerate(products):
            base_qty = DEFAULT_STOCKS[prod_idx % len(DEFAULT_STOCKS)]
            adjusted_qty = max(1, base_qty + (store_idx if base_qty > 5 else 0))
            inv = StoreInventory(
                store_id=store.id,
                product_id=product.id,
                stock_available=adjusted_qty,
                stock_reserved=0,
                reorder_threshold=5,
            )
            db.add(inv)

        for rider_name, d_lat, d_lng in RIDERS_BY_STORE[store.name]:
            rider = Rider(
                store_id=store.id,
                name=rider_name,
                status="IDLE",
                current_lat=round(store.lat + d_lat, 6),
                current_lng=round(store.lng + d_lng, 6),
            )
            db.add(rider)

    db.flush()

    # Seed historical delivered orders with realistic order_events for analytics
    now = datetime.now(timezone.utc)
    historical_samples = [
        (0, "Ananya Sharma", 0.006, 0.005, [0, 3, 6], 410, 0.14, 125, 45, 220),
        (0, "Rahul Menon", -0.007, 0.004, [1, 7, 10, 13], 495, 0.28, 160, 50, 265),
        (0, "Priya Iyer", 0.009, -0.008, [2, 8, 12, 16, 17], 625, 0.68, 215, 65, 345),
        (0, "Siddharth Joshi", -0.004, -0.005, [4, 14], 385, 0.11, 105, 40, 215),
        (1, "Meera Krishnan", 0.005, 0.007, [0, 6, 11, 15], 455, 0.21, 135, 45, 255),
        (1, "Aditya Patel", -0.008, 0.006, [5, 9, 12, 13], 530, 0.42, 175, 55, 290),
        (1, "Kavya Bhat", 0.011, -0.007, [1, 2, 7, 10, 16], 640, 0.74, 225, 70, 355),
        (2, "Varun Deshmukh", 0.005, -0.004, [3, 6, 14, 15], 430, 0.18, 130, 40, 235),
    ]

    for idx, (
        store_idx,
        customer,
        d_lat,
        d_lng,
        prod_indices,
        pred_eta,
        risk,
        pick_sec,
        pack_sec,
        deliver_sec,
    ) in enumerate(historical_samples):
        store = stores[store_idx]
        store_riders = db.query(Rider).filter(Rider.store_id == store.id).all()
        rider = store_riders[idx % len(store_riders)]

        created_at = now - timedelta(minutes=110 - idx * 12)
        order = Order(
            store_id=store.id,
            customer_name=customer,
            delivery_lat=round(store.lat + d_lat, 6),
            delivery_lng=round(store.lng + d_lng, 6),
            status="DELIVERED",
            created_at=created_at,
            predicted_eta_sec=pred_eta,
            sla_risk_score=risk,
            rider_id=rider.id,
        )
        db.add(order)
        db.flush()

        for p_idx in prod_indices:
            p = products[p_idx]
            db.add(
                OrderItem(
                    order_id=order.id,
                    product_id=p.id,
                    quantity=1,
                    unit_price_inr=p.price_inr,
                )
            )

        t0 = created_at
        t1 = t0 + timedelta(seconds=20)
        t2 = t1 + timedelta(seconds=pick_sec)
        t3 = t2 + timedelta(seconds=pack_sec)
        t4 = t3 + timedelta(seconds=deliver_sec)

        events = [
            OrderEvent(order_id=order.id, from_status=None, to_status="PLACED", timestamp=t0, note="Order created"),
            OrderEvent(order_id=order.id, from_status="PLACED", to_status="PICKING", timestamp=t1, note="Picker assigned"),
            OrderEvent(order_id=order.id, from_status="PICKING", to_status="PACKED", timestamp=t2, note="Bag sealed at dispatch bay"),
            OrderEvent(order_id=order.id, from_status="PACKED", to_status="OUT_FOR_DELIVERY", timestamp=t3, note=f"Rider {rider.name} departed hub"),
            OrderEvent(order_id=order.id, from_status="OUT_FOR_DELIVERY", to_status="DELIVERED", timestamp=t4, note="Handed over to customer"),
        ]
        db.add_all(events)

    # Seed two active orders for immediate Ops Console visibility
    active_samples = [
        (0, "Neha Kulkarni", 0.008, 0.006, [0, 1, 7, 13], "PLACED", 575, 0.72, 185),
        (0, "Rohan Deshpande", -0.005, 0.004, [3, 6, 10], "PICKING", 440, 0.24, 95),
    ]
    for store_idx, customer, d_lat, d_lng, prod_indices, status, pred_eta, risk, age_sec in active_samples:
        store = stores[store_idx]
        created_at = now - timedelta(seconds=age_sec)
        order = Order(
            store_id=store.id,
            customer_name=customer,
            delivery_lat=round(store.lat + d_lat, 6),
            delivery_lng=round(store.lng + d_lng, 6),
            status=status,
            created_at=created_at,
            predicted_eta_sec=pred_eta,
            sla_risk_score=risk,
            rider_id=None,
        )
        db.add(order)
        db.flush()

        for p_idx in prod_indices:
            p = products[p_idx]
            db.add(
                OrderItem(
                    order_id=order.id,
                    product_id=p.id,
                    quantity=1,
                    unit_price_inr=p.price_inr,
                )
            )

        db.add(OrderEvent(order_id=order.id, from_status=None, to_status="PLACED", timestamp=created_at, note="Order created"))
        if status == "PICKING":
            db.add(
                OrderEvent(
                    order_id=order.id,
                    from_status="PLACED",
                    to_status="PICKING",
                    timestamp=created_at + timedelta(seconds=25),
                    note="Picker started aisle sweep",
                )
            )

    db.commit()
    return True


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        seeded = seed_database(session)
        print("Database seeded." if seeded else "Database already contains data.")
    finally:
        session.close()
