from concurrent.futures import ThreadPoolExecutor
import threading

from app.models import StoreInventory


def test_concurrent_checkout_last_unit_prevents_oversell(
    client, db_session_factory, customer1_headers, customer2_headers
):
    """
    Two simultaneous checkouts for a 1-unit SKU (product_id=2) must result in
    exactly one HTTP 201 Created and one HTTP 409 Conflict with zero overselling.
    """
    barrier = threading.Barrier(2)

    def place_order(customer_label: str, headers: dict) -> int:
        barrier.wait()
        response = client.post(
            "/api/orders",
            headers=headers,
            json={
                "store_id": 1,
                "customer_name": customer_label,
                "delivery_lat": 12.9150,
                "delivery_lng": 77.6420,
                "items": [{"product_id": 2, "quantity": 1}],
            },
        )
        return response.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(place_order, "Concurrent Buyer A", customer1_headers),
            pool.submit(place_order, "Concurrent Buyer B", customer2_headers),
        ]
        statuses = sorted(f.result() for f in futures)

    assert statuses == [201, 409]

    # Verify database integrity: stock_available == 0, stock_reserved == 1
    db = db_session_factory()
    try:
        inv = (
            db.query(StoreInventory)
            .filter(StoreInventory.store_id == 1, StoreInventory.product_id == 2)
            .first()
        )
        assert inv.stock_available == 0
        assert inv.stock_reserved == 1
    finally:
        db.close()
