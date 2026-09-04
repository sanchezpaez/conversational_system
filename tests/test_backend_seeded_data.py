from app.backend import MockBackendClient


def test_mock_backend_client_uses_seeded_sqlite_data(tmp_path):
    db_path = tmp_path / "orders.db"
    client = MockBackendClient(db_path=str(db_path))

    status = client.get_order_status("AB-123")

    assert status["ok"] is True
    assert status["code"] == "order_status"
    assert status["order_id"] == "AB-123"
    assert status["status"] == "processing"
    assert status["booking_date"] == "2026-09-12"

    changed = client.change_booking("AB-123", "2026-12-20")

    assert changed["ok"] is True
    assert changed["code"] == "booking_changed"
    assert changed["new_date"] == "2026-12-20"
    assert client.get_order_status("AB-123")["booking_date"] == "2026-12-20"


def test_mock_backend_client_keeps_generic_fallback_for_unknown_orders(tmp_path):
    client = MockBackendClient(db_path=str(tmp_path / "orders.db"))

    result = client.get_order_status("NOT-FOUND")

    assert result["ok"] is True
    assert result["code"] == "order_status"
    assert result["order_id"] == "NOT-FOUND"
