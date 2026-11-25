def _create_sample_order(client, headers, store_id=1, product_id=1, quantity=2):
    resp = client.post(
        "/api/orders",
        headers=headers,
        json={
            "store_id": store_id,
            "customer_name": "Test Customer",
            "delivery_lat": 12.9150,
            "delivery_lng": 77.6420,
            "items": [{"product_id": product_id, "quantity": quantity}],
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_full_valid_lifecycle_and_nearest_rider_assignment(
    client, customer1_headers, hsr_admin_headers
):
    order = _create_sample_order(client, customer1_headers, store_id=1, product_id=1, quantity=2)
    order_id = order["id"]
    assert order["status"] == "PLACED"
    assert len(order["events"]) == 1

    # PLACED -> PICKING
    r1 = client.patch(
        f"/api/orders/{order_id}/status",
        headers=hsr_admin_headers,
        json={"status": "PICKING"},
    )
    assert r1.status_code == 200
    assert r1.json()["status"] == "PICKING"

    # PICKING -> PACKED (should auto-assign nearest IDLE rider: "Near Rider")
    r2 = client.patch(
        f"/api/orders/{order_id}/status",
        headers=hsr_admin_headers,
        json={"status": "PACKED"},
    )
    assert r2.status_code == 200
    packed = r2.json()
    assert packed["status"] == "PACKED"
    assert packed["rider_name"] == "Near Rider"

    # PACKED -> OUT_FOR_DELIVERY
    r3 = client.patch(
        f"/api/orders/{order_id}/status",
        headers=hsr_admin_headers,
        json={"status": "OUT_FOR_DELIVERY"},
    )
    assert r3.status_code == 200
    assert r3.json()["status"] == "OUT_FOR_DELIVERY"

    # OUT_FOR_DELIVERY -> DELIVERED
    r4 = client.patch(
        f"/api/orders/{order_id}/status",
        headers=hsr_admin_headers,
        json={"status": "DELIVERED"},
    )
    assert r4.status_code == 200
    delivered = r4.json()
    assert delivered["status"] == "DELIVERED"
    assert len(delivered["events"]) == 5

    # Rider should return to IDLE after delivery
    riders = client.get("/api/riders?store_id=1", headers=hsr_admin_headers).json()
    near_rider = next(r for r in riders if r["name"] == "Near Rider")
    assert near_rider["status"] == "IDLE"


def test_invalid_state_transitions_rejected_with_400(
    client, customer1_headers, hsr_admin_headers
):
    order = _create_sample_order(client, customer1_headers, store_id=1, product_id=1, quantity=1)
    order_id = order["id"]

    # Invalid jump: PLACED -> PACKED
    bad1 = client.patch(
        f"/api/orders/{order_id}/status",
        headers=hsr_admin_headers,
        json={"status": "PACKED"},
    )
    assert bad1.status_code == 400

    # Invalid jump: PLACED -> DELIVERED
    bad2 = client.patch(
        f"/api/orders/{order_id}/status",
        headers=hsr_admin_headers,
        json={"status": "DELIVERED"},
    )
    assert bad2.status_code == 400

    # Advance to OUT_FOR_DELIVERY and verify CANCELLED is rejected after dispatch
    assert (
        client.patch(f"/api/orders/{order_id}/status", headers=hsr_admin_headers, json={"status": "PICKING"}).status_code
        == 200
    )
    assert (
        client.patch(f"/api/orders/{order_id}/status", headers=hsr_admin_headers, json={"status": "PACKED"}).status_code
        == 200
    )
    assert (
        client.patch(f"/api/orders/{order_id}/status", headers=hsr_admin_headers, json={"status": "OUT_FOR_DELIVERY"}).status_code
        == 200
    )

    bad3 = client.patch(
        f"/api/orders/{order_id}/status",
        headers=hsr_admin_headers,
        json={"status": "CANCELLED"},
    )
    assert bad3.status_code == 400


def test_cancellation_restores_inventory_atomically(
    client, customer1_headers
):
    before = client.get("/api/stores/1/inventory").json()
    milk_before = next(i for i in before if i["product_id"] == 1)
    assert milk_before["stock_available"] == 10

    order = _create_sample_order(client, customer1_headers, store_id=1, product_id=1, quantity=3)
    after_order = client.get("/api/stores/1/inventory").json()
    milk_after_order = next(i for i in after_order if i["product_id"] == 1)
    assert milk_after_order["stock_available"] == 7
    assert milk_after_order["stock_reserved"] == 3

    cancel_resp = client.post(
        f"/api/orders/{order['id']}/cancel",
        headers=customer1_headers,
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"

    after_cancel = client.get("/api/stores/1/inventory").json()
    milk_after_cancel = next(i for i in after_cancel if i["product_id"] == 1)
    assert milk_after_cancel["stock_available"] == 10
    assert milk_after_cancel["stock_reserved"] == 0
