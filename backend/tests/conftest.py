import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.auth import ROLE_BRANCH_ADMIN, ROLE_CUSTOMER, create_access_token, hash_password
from app.database import Base, get_db
from app.main import app
from app.models import Product, Rider, Store, StoreInventory, User
from app.services.ml_inference import sla_predictor


@pytest.fixture()
def test_db_engine():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False, "timeout": 30},
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture()
def db_session_factory(test_db_engine):
    factory = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    db = factory()
    try:
        hsr = Store(id=1, name="HSR Layout Hub", lat=12.9116, lng=77.6389, active_pickers=5)
        kora = Store(id=2, name="Koramangala Hub", lat=12.9352, lng=77.6245, active_pickers=6)
        db.add_all([hsr, kora])
        db.flush()

        p1 = Product(
            sku="TST-001",
            name="Test Milk 500ml",
            category="Dairy",
            aisle_code="A1-Dairy",
            price_inr=30.0,
            image_url="/assets/products/Nandhini goodlife toned milk 500 ML.jpeg",
        )
        p2 = Product(
            sku="TST-002",
            name="Test Avocado Single",
            category="Produce",
            aisle_code="A3-Produce",
            price_inr=165.0,
            image_url="/assets/products/Hass Avocado Single Piece.jpeg",
        )
        db.add_all([p1, p2])
        db.flush()

        db.add_all(
            [
                StoreInventory(store_id=1, product_id=p1.id, stock_available=10, stock_reserved=0, reorder_threshold=4),
                StoreInventory(store_id=1, product_id=p2.id, stock_available=1, stock_reserved=0, reorder_threshold=4),
                StoreInventory(store_id=2, product_id=p1.id, stock_available=12, stock_reserved=0, reorder_threshold=4),
                StoreInventory(store_id=2, product_id=p2.id, stock_available=3, stock_reserved=0, reorder_threshold=4),
            ]
        )

        # Two riders in HSR (store 1) at different distances to verify nearest-rider assignment
        r_far = Rider(store_id=1, name="Far Rider", status="IDLE", current_lat=12.9280, current_lng=77.6550)
        r_near = Rider(store_id=1, name="Near Rider", status="IDLE", current_lat=12.9119, current_lng=77.6392)
        # One rider in Koramangala (store 2)
        r_kora = Rider(store_id=2, name="Kora Rider", status="IDLE", current_lat=12.9355, current_lng=77.6248)
        db.add_all([r_far, r_near, r_kora])

        # Two Branch Admins and two Customers
        hsr_admin = User(
            email="hsr.admin@swifthub.com",
            full_name="HSR Layout Hub Admin",
            password_hash=hash_password("AdminHSR123!"),
            role=ROLE_BRANCH_ADMIN,
            store_id=1,
        )
        kora_admin = User(
            email="koramangala.admin@swifthub.com",
            full_name="Koramangala Hub Admin",
            password_hash=hash_password("AdminKora123!"),
            role=ROLE_BRANCH_ADMIN,
            store_id=2,
        )
        cust1 = User(
            email="customer1@gmail.com",
            full_name="Customer One",
            password_hash=hash_password("Pass1234!"),
            role=ROLE_CUSTOMER,
            store_id=None,
        )
        cust2 = User(
            email="customer2@gmail.com",
            full_name="Customer Two",
            password_hash=hash_password("Pass1234!"),
            role=ROLE_CUSTOMER,
            store_id=None,
        )
        db.add_all([hsr_admin, kora_admin, cust1, cust2])
        db.commit()
    finally:
        db.close()

    return factory


@pytest.fixture()
def client(db_session_factory):
    sla_predictor.load()

    def override_get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _headers_for_email(db_session_factory, email: str) -> dict:
    db = db_session_factory()
    try:
        user = db.query(User).filter(User.email == email).first()
        token = create_access_token(user)
        return {"Authorization": f"Bearer {token}"}
    finally:
        db.close()


@pytest.fixture()
def hsr_admin_headers(db_session_factory):
    return _headers_for_email(db_session_factory, "hsr.admin@swifthub.com")


@pytest.fixture()
def kora_admin_headers(db_session_factory):
    return _headers_for_email(db_session_factory, "koramangala.admin@swifthub.com")


@pytest.fixture()
def customer1_headers(db_session_factory):
    return _headers_for_email(db_session_factory, "customer1@gmail.com")


@pytest.fixture()
def customer2_headers(db_session_factory):
    return _headers_for_email(db_session_factory, "customer2@gmail.com")
