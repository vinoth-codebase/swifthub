import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import Product, Rider, Store, StoreInventory
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
        store = Store(name="Koramangala Hub", lat=12.9352, lng=77.6245, active_pickers=5)
        db.add(store)
        db.flush()

        p1 = Product(
            sku="TST-001",
            name="Test Milk 500ml",
            category="Dairy",
            aisle_code="A1-Dairy",
            price_inr=35.0,
        )
        p2 = Product(
            sku="TST-002",
            name="Test Avocado Single",
            category="Produce",
            aisle_code="A3-Produce",
            price_inr=160.0,
        )
        db.add_all([p1, p2])
        db.flush()

        db.add_all(
            [
                StoreInventory(
                    store_id=store.id,
                    product_id=p1.id,
                    stock_available=10,
                    stock_reserved=0,
                    reorder_threshold=3,
                ),
                StoreInventory(
                    store_id=store.id,
                    product_id=p2.id,
                    stock_available=1,
                    stock_reserved=0,
                    reorder_threshold=2,
                ),
            ]
        )

        # Two riders at different distances from hub to verify nearest-rider assignment
        r_far = Rider(
            store_id=store.id,
            name="Far Rider",
            status="IDLE",
            current_lat=12.9500,
            current_lng=77.6400,
        )
        r_near = Rider(
            store_id=store.id,
            name="Near Rider",
            status="IDLE",
            current_lat=12.9355,
            current_lng=77.6248,
        )
        db.add_all([r_far, r_near])
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
