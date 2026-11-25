from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.auth import ROLE_BRANCH_ADMIN, ROLE_CUSTOMER, hash_password
from app.database import Base, SessionLocal, engine
from app.models import (
    Order,
    OrderEvent,
    OrderItem,
    Product,
    Rider,
    Store,
    StoreInventory,
    User,
)

# Exactly 2 dark-store branches:
# store_id=1 -> HSR Layout Hub
# store_id=2 -> Koramangala Hub
STORES_DATA = [
    {"id": 1, "name": "HSR Layout Hub", "lat": 12.9116, "lng": 77.6389, "active_pickers": 5},
    {"id": 2, "name": "Koramangala Hub", "lat": 12.9352, "lng": 77.6245, "active_pickers": 6},
]

BRANCH_ADMINS_DATA = [
    {
        "email": "hsr.admin@swifthub.com",
        "full_name": "HSR Layout Hub Admin",
        "password": "AdminHSR123!",
        "role": ROLE_BRANCH_ADMIN,
        "store_id": 1,
    },
    {
        "email": "koramangala.admin@swifthub.com",
        "full_name": "Koramangala Hub Admin",
        "password": "AdminKora123!",
        "role": ROLE_BRANCH_ADMIN,
        "store_id": 2,
    },
]

DEMO_CUSTOMERS_DATA = [
    {
        "email": "aarav.demo@gmail.com",
        "full_name": "Aarav Sharma",
        "password": "Customer123!",
        "role": ROLE_CUSTOMER,
        "store_id": None,
    },
    {
        "email": "priya.demo@gmail.com",
        "full_name": "Priya Nair",
        "password": "Customer123!",
        "role": ROLE_CUSTOMER,
        "store_id": None,
    },
]

# Exact 18-product catalog with local static product images
PRODUCTS_DATA = [
    # Dairy (A1-Dairy)
    {
        "sku": "DAI-001",
        "name": "Nandini Goodlife Toned Milk 500ml",
        "category": "Dairy",
        "aisle_code": "A1-Dairy",
        "price_inr": 30.0,
        "image_url": "/assets/products/Nandhini goodlife toned milk 500 ML.jpeg",
    },
    {
        "sku": "DAI-002",
        "name": "Amul Malai Paneer 200g",
        "category": "Dairy",
        "aisle_code": "A1-Dairy",
        "price_inr": 95.0,
        "image_url": "/assets/products/Amul malai panner.jpeg",
    },
    {
        "sku": "DAI-003",
        "name": "Epigamia Greek Yogurt",
        "category": "Dairy",
        "aisle_code": "A1-Dairy",
        "price_inr": 65.0,
        "image_url": "/assets/products/Epigamia greek yogurt.jpeg",
    },
    # Bakery (A2-Bakery)
    {
        "sku": "BAK-001",
        "name": "Britannia Whole Wheat Bread 400g",
        "category": "Bakery",
        "aisle_code": "A2-Bakery",
        "price_inr": 55.0,
        "image_url": "/assets/products/Britannia Whole Wheat Bread 400g.jpeg",
    },
    {
        "sku": "BAK-002",
        "name": "Artisan Sourdough Loaf 350g",
        "category": "Bakery",
        "aisle_code": "A2-Bakery",
        "price_inr": 180.0,
        "image_url": "/assets/products/Artisan Sourdough Loaf 350g.jpeg",
    },
    {
        "sku": "BAK-003",
        "name": "Butter Croissant (Pack of 2)",
        "category": "Bakery",
        "aisle_code": "A2-Bakery",
        "price_inr": 140.0,
        "image_url": "/assets/products/Butter Croissant Pack of 2.jpeg",
    },
    # Produce (A3-Produce)
    {
        "sku": "PRO-001",
        "name": "Farm Fresh Robusta Bananas 500g",
        "category": "Produce",
        "aisle_code": "A3-Produce",
        "price_inr": 45.0,
        "image_url": "/assets/products/Farm Fresh Robusta Bananas 500g.jpeg",
    },
    {
        "sku": "PRO-002",
        "name": "Baby Spinach Washed 200g",
        "category": "Produce",
        "aisle_code": "A3-Produce",
        "price_inr": 60.0,
        "image_url": "/assets/products/Baby Spinach Washed 200g.jpeg",
    },
    {
        "sku": "PRO-003",
        "name": "Hass Avocado (Single Piece)",
        "category": "Produce",
        "aisle_code": "A3-Produce",
        "price_inr": 165.0,
        "image_url": "/assets/products/Hass Avocado Single Piece.jpeg",
    },
    {
        "sku": "PRO-004",
        "name": "Organic Cherry Tomatoes 250g",
        "category": "Produce",
        "aisle_code": "A3-Produce",
        "price_inr": 85.0,
        "image_url": "/assets/products/Organic Cherry Tomatoes 250g.jpeg",
    },
    # Snacks (A4-Snacks)
    {
        "sku": "SNK-001",
        "name": "Amul Dark Chocolate Bar",
        "category": "Snacks",
        "aisle_code": "A4-Snacks",
        "price_inr": 110.0,
        "image_url": "/assets/products/Amul Dark Chocolate Bar .jpeg",
    },
    {
        "sku": "SNK-002",
        "name": "Happilo Roasted Makhana Peri Peri 60g",
        "category": "Snacks",
        "aisle_code": "A4-Snacks",
        "price_inr": 125.0,
        "image_url": "/assets/products/Hapillo Roasted Makhana Peri Peri 60g.jpeg",
    },
    {
        "sku": "SNK-003",
        "name": "Lay's Cheese & Onion Chips",
        "category": "Snacks",
        "aisle_code": "A4-Snacks",
        "price_inr": 40.0,
        "image_url": "/assets/products/Lays cheese onion chips.jpeg",
    },
    # Beverages (A5-Beverages)
    {
        "sku": "BEV-001",
        "name": "Cold Brew Coffee Classic 250ml",
        "category": "Beverages",
        "aisle_code": "A5-Beverages",
        "price_inr": 130.0,
        "image_url": "/assets/products/Cold Brew Coffee Classic 250ml.jpeg",
    },
    {
        "sku": "BEV-002",
        "name": "Raw Pressery Valencia Orange 200ml",
        "category": "Beverages",
        "aisle_code": "A5-Beverages",
        "price_inr": 90.0,
        "image_url": "/assets/products/Raw Pressery Valencia Orange 200ml.jpeg",
    },
    {
        "sku": "BEV-003",
        "name": "Tender Coconut Water 200ml",
        "category": "Beverages",
        "aisle_code": "A5-Beverages",
        "price_inr": 55.0,
        "image_url": "/assets/products/Tender Coconut Water 200ml.jpeg",
    },
    # Pantry (A6-Pantry)
    {
        "sku": "PAN-001",
        "name": "Cold Pressed Groundnut Oil 1L",
        "category": "Pantry",
        "aisle_code": "A6-Pantry",
        "price_inr": 320.0,
        "image_url": "/assets/products/Cold Pressed Groundnut Oil 1L.jpeg",
    },
    {
        "sku": "PAN-002",
        "name": "iD Fresh Idli & Dosa Batter 1kg",
        "category": "Pantry",
        "aisle_code": "A6-Pantry",
        "price_inr": 95.0,
        "image_url": "/assets/products/ID Fresh Idli Dosa Batter 1kg.jpeg",
    },
]

# Slightly varied stock levels per branch, including several items in 1..4 so Low Stock badges appear
STOCKS_BY_STORE = {
    1: [18, 3, 12, 16, 2, 9, 22, 14, 1, 4, 15, 8, 20, 2, 14, 19, 6, 3],
    2: [24, 11, 4, 14, 7, 3, 19, 10, 2, 13, 3, 12, 17, 9, 4, 21, 2, 10],
}

RIDERS_BY_STORE = {
    "HSR Layout Hub": [
        ("Nikhil Verma", 0.0022, 0.0012),
        ("Santosh Reddy", -0.0016, 0.0025),
        ("Harish Murthy", 0.0011, -0.0017),
        ("Ajay Kulkarni", -0.0020, -0.0013),
    ],
    "Koramangala Hub": [
        ("Arjun Rao", 0.0020, -0.0015),
        ("Karthik Nair", -0.0018, 0.0022),
        ("Deepak Gowda", 0.0012, 0.0018),
        ("Suresh Babu", -0.0025, -0.0010),
    ],
}


def seed_database(db: Session, force_reset: bool = False) -> bool:
    """Seed exactly 2 branches, 2 Branch Admins, 18 products, inventory, riders, and operational history."""
    if force_reset:
        db.query(OrderEvent).delete()
        db.query(OrderItem).delete()
        db.query(Order).delete()
        db.query(StoreInventory).delete()
        db.query(Rider).delete()
        db.query(User).delete()
        db.query(Product).delete()
        db.query(Store).delete()
        db.commit()
    elif db.query(Store).count() > 0:
        # Ensure branch admin and demo customer accounts exist even on existing databases
        _ensure_seed_users(db)
        db.commit()
        return False

    stores: list[Store] = []
    for s_data in STORES_DATA:
        store = Store(**s_data)
        db.add(store)
        stores.append(store)
    db.flush()

    seeded_users = _ensure_seed_users(db)
    aarav_user = seeded_users["aarav.demo@gmail.com"]
    priya_user = seeded_users["priya.demo@gmail.com"]

    products: list[Product] = []
    for p_data in PRODUCTS_DATA:
        product = Product(**p_data)
        db.add(product)
        products.append(product)
    db.flush()

    for store in stores:
        stock_list = STOCKS_BY_STORE[store.id]
        for prod_idx, product in enumerate(products):
            inv = StoreInventory(
                store_id=store.id,
                product_id=product.id,
                stock_available=stock_list[prod_idx],
                stock_reserved=0,
                reorder_threshold=4,
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

    # Seed historical delivered orders across both branches for Ops Analytics
    now = datetime.now(timezone.utc)
    historical_samples = [
        # HSR Layout Hub (store_idx=0, store_id=1) — first order linked to Aarav Sharma
        (0, aarav_user.id, "Aarav Sharma", 0.006, 0.005, [0, 3, 6], 410, 0.14, 125, 45, 220),
        (0, None, "Rahul Menon", -0.007, 0.004, [1, 7, 10, 13], 495, 0.28, 160, 50, 265),
        (0, None, "Ananya Iyer", 0.009, -0.008, [2, 8, 12, 16, 17], 625, 0.68, 215, 65, 345),
        (0, None, "Siddharth Joshi", -0.004, -0.005, [4, 14], 385, 0.11, 105, 40, 215),
        # Koramangala Hub (store_idx=1, store_id=2) — first order linked to Priya Nair
        (1, priya_user.id, "Priya Nair", 0.005, 0.007, [0, 6, 11, 15], 455, 0.21, 135, 45, 255),
        (1, None, "Aditya Patel", -0.008, 0.006, [5, 9, 12, 13], 530, 0.42, 175, 55, 290),
        (1, None, "Kavya Bhat", 0.011, -0.007, [1, 2, 7, 10, 16], 640, 0.74, 225, 70, 355),
        (1, None, "Varun Deshmukh", 0.005, -0.004, [3, 6, 14, 15], 430, 0.18, 130, 40, 235),
    ]

    for idx, (
        store_idx,
        customer_id,
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
            customer_id=customer_id,
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

    # Seed active orders in BOTH hubs (including 1 active order linked to each Demo Customer)
    active_samples = [
        (0, aarav_user.id, "Aarav Sharma", 0.008, 0.006, [0, 1, 9, 13], "PICKING", 540, 0.66, 165),
        (0, None, "Rohan Deshpande", -0.005, 0.004, [3, 6, 10], "PLACED", 440, 0.24, 95),
        (1, priya_user.id, "Priya Nair", 0.007, -0.006, [2, 5, 11, 14], "PICKING", 535, 0.64, 150),
        (1, None, "Karan Malhotra", -0.006, 0.005, [0, 4, 12], "PLACED", 430, 0.26, 80),
    ]
    for store_idx, customer_id, customer, d_lat, d_lng, prod_indices, status, pred_eta, risk, age_sec in active_samples:
        store = stores[store_idx]
        created_at = now - timedelta(seconds=age_sec)
        order = Order(
            store_id=store.id,
            customer_id=customer_id,
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


def _ensure_seed_users(db: Session) -> dict[str, User]:
    users_by_email: dict[str, User] = {}
    for user_data in BRANCH_ADMINS_DATA + DEMO_CUSTOMERS_DATA:
        existing = db.query(User).filter(User.email == user_data["email"]).first()
        if not existing:
            existing = User(
                email=user_data["email"],
                full_name=user_data["full_name"],
                password_hash=hash_password(user_data["password"]),
                role=user_data["role"],
                store_id=user_data["store_id"],
            )
            db.add(existing)
        users_by_email[user_data["email"]] = existing
    db.flush()
    return users_by_email


if __name__ == "__main__":
    import sys

    reset = "--reset" in sys.argv
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        seeded = seed_database(session, force_reset=reset)
        print("Database seeded." if seeded else "Database already contains data.")
    finally:
        session.close()
