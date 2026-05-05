from app.backend_real import RealBackendClient


def test_real_backend_client_order_status_success(monkeypatch):
    client = RealBackendClient(base_url="https://backend.example", api_key="secret")

    monkeypatch.setattr(
        client,
        "_post_json",
        lambda _path, _payload: {
            "ok": True,
            "order_id": "AB-123",
            "status": "shipped",
        },
    )

    result = client.get_order_status("AB-123")

    assert result["ok"] is True
    assert result["code"] == "order_status"
    assert result["order_id"] == "AB-123"
    assert result["status"] == "shipped"


def test_real_backend_client_change_booking_success(monkeypatch):
    client = RealBackendClient(base_url="https://backend.example", api_key="secret")

    monkeypatch.setattr(
        client,
        "_post_json",
        lambda _path, _payload: {
            "ok": True,
            "order_id": "7821",
            "new_date": "2026-08-10",
        },
    )

    result = client.change_booking("7821", "2026-08-10")

    assert result["ok"] is True
    assert result["code"] == "booking_changed"
    assert result["order_id"] == "7821"
    assert result["new_date"] == "2026-08-10"


def test_real_backend_client_returns_unavailable_on_request_error(monkeypatch):
    client = RealBackendClient(base_url="https://backend.example", api_key="secret")

    monkeypatch.setattr(
        client,
        "_post_json",
        lambda _path, _payload: {
            "ok": False,
            "code": "backend_unavailable",
            "message": "Backend service is unavailable.",
        },
    )

    result = client.get_order_status("AB-123")

    assert result["ok"] is False
    assert result["code"] == "backend_unavailable"
