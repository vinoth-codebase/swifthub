from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import verify_password
from app.database import Base
from app.models import Order, Product, Store, User
from app.seed import seed_database


def test_customer_registration_login_and_me(client):
    reg = client.post(
        "/api/auth/register",
        json={
            "full_name": "New Shopper",
            "email": "new.shopper@gmail.com",
            "password": "StrongPassword123",
        },
    )
    assert reg.status_code == 201
    data = reg.json()
    assert data["user"]["role"] == "CUSTOMER"
    assert data["user"]["store_id"] is None
    assert data["access_token"]

    # Duplicate email rejected
    dup = client.post(
        "/api/auth/register",
        json={
            "full_name": "Duplicate Shopper",
            "email": "new.shopper@gmail.com",
            "password": "StrongPassword123",
        },
    )
    assert dup.status_code == 409

    # Login with valid password
    login = client.post(
        "/api/auth/login",
        json={"email": "new.shopper@gmail.com", "password": "StrongPassword123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "new.shopper@gmail.com"

    # Invalid password rejected
    bad_login = client.post(
        "/api/auth/login",
        json={"email": "new.shopper@gmail.com", "password": "WrongPassword"},
    )
    assert bad_login.status_code == 401


def test_admin_endpoints_reject_unauthenticated_and_customer(client, customer1_headers):
    # Unauthenticated -> 401
    assert client.get("/api/riders").status_code == 401
    assert client.get("/api/analytics").status_code == 401
    assert client.get("/api/orders").status_code == 401
    assert client.post("/api/stores/1/inventory/1/restock", json={"quantity": 5}).status_code == 401

    # Customer -> 403 on admin endpoints
    assert client.get("/api/riders", headers=customer1_headers).status_code == 403
    assert client.get("/api/analytics", headers=customer1_headers).status_code == 403
    assert (
        client.post(
            "/api/stores/1/inventory/1/restock",
            headers=customer1_headers,
            json={"quantity": 5},
        ).status_code
        == 403
    )
    assert (
        client.post("/api/simulation/trigger", headers=customer1_headers, json={"store_id": 1}).status_code
        == 403
    )


def test_branch_admin_strict_tenant_isolation(
    client, customer1_headers, hsr_admin_headers, kora_admin_headers
):
    # Customer places an order at Koramangala Hub (store_id=2)
    kora_order = client.post(
        "/api/orders",
        headers=customer1_headers,
        json={
            "store_id": 2,
            "customer_name": "Customer One",
            "delivery_lat": 12.9390,
            "delivery_lng": 77.6280,
            "items": [{"product_id": 1, "quantity": 1}],
        },
    ).json()

    # HSR Admin (store_id=1) cannot inspect, update, restock, or view riders/analytics for Koramangala (store_id=2)
    assert client.get("/api/stores/2/inventory", headers=hsr_admin_headers).status_code == 403
    assert (
        client.post(
            "/api/stores/2/inventory/1/restock",
            headers=hsr_admin_headers,
            json={"quantity": 10},
        ).status_code
        == 403
    )
    assert client.get("/api/riders?store_id=2", headers=hsr_admin_headers).status_code == 403
    assert client.get("/api/analytics?store_id=2", headers=hsr_admin_headers).status_code == 403
    assert client.get("/api/orders?store_id=2", headers=hsr_admin_headers).status_code == 403
    assert client.get(f"/api/orders/{kora_order['id']}", headers=hsr_admin_headers).status_code == 403
    assert (
        client.patch(
            f"/api/orders/{kora_order['id']}/status",
            headers=hsr_admin_headers,
            json={"status": "PICKING"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/simulation/trigger",
            headers=hsr_admin_headers,
            json={"store_id": 2},
        ).status_code
        == 403
    )

    # Koramangala Admin (store_id=2) CAN view and advance Koramangala's order
    assert client.get(f"/api/orders/{kora_order['id']}", headers=kora_admin_headers).status_code == 200
    assert (
        client.patch(
            f"/api/orders/{kora_order['id']}/status",
            headers=kora_admin_headers,
            json={"status": "PICKING"},
        ).status_code
        == 200
    )


def test_customer_order_isolation(client, customer1_headers, customer2_headers):
    ord1 = client.post(
        "/api/orders",
        headers=customer1_headers,
        json={
            "store_id": 1,
            "customer_name": "Customer One",
            "delivery_lat": 12.9150,
            "delivery_lng": 77.6420,
            "items": [{"product_id": 1, "quantity": 1}],
        },
    ).json()

    # Customer 2 cannot view or cancel Customer 1's order
    assert client.get(f"/api/orders/{ord1['id']}", headers=customer2_headers).status_code == 403
    assert client.post(f"/api/orders/{ord1['id']}/cancel", headers=customer2_headers).status_code == 403

    # Customer 2's order list is empty; Customer 1's has ord1
    assert client.get("/api/orders", headers=customer2_headers).json() == []
    c1_orders = client.get("/api/orders", headers=customer1_headers).json()
    assert len(c1_orders) == 1
    assert c1_orders[0]["id"] == ord1["id"]


def test_seeder_creates_exact_2_branches_2_admins_and_18_products():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        assert seed_database(db) is True

        stores = db.query(Store).order_by(Store.id.asc()).all()
        assert [(s.id, s.name) for s in stores] == [
            (1, "HSR Layout Hub"),
            (2, "Koramangala Hub"),
        ]

        admins = db.query(User).filter(User.role == "BRANCH_ADMIN").order_by(User.store_id.asc()).all()
        assert [(a.email, a.store_id) for a in admins] == [
            ("hsr.admin@swifthub.com", 1),
            ("koramangala.admin@swifthub.com", 2),
        ]

        customers = db.query(User).filter(User.role == "CUSTOMER").order_by(User.email.asc()).all()
        assert [(c.email, c.full_name, c.store_id) for c in customers] == [
            ("aarav.demo@gmail.com", "Aarav Sharma", None),
            ("priya.demo@gmail.com", "Priya Nair", None),
        ]
        assert all(verify_password("Customer123!", c.password_hash) for c in customers)

        aarav, priya = customers
        aarav_orders = db.query(Order).filter(Order.customer_id == aarav.id, Order.store_id == 1).all()
        priya_orders = db.query(Order).filter(Order.customer_id == priya.id, Order.store_id == 2).all()
        assert len(aarav_orders) >= 1
        assert len(priya_orders) >= 1

        products = db.query(Product).all()
        assert len(products) == 18
        assert all(p.image_url and p.image_url.startswith("/assets/products/") for p in products)
    finally:
        db.close()
        engine.dispose()
