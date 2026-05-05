from datetime import date
from typing import Protocol


class BackendClient(Protocol):
    def get_order_status(self, order_id: str | None) -> dict:
        ...

    def change_booking(self, order_id: str | None, new_date: str | None) -> dict:
        ...

    def fallback_support(self) -> dict:
        ...


def get_order_status(order_id: str | None) -> dict:
    if not order_id:
        return {
            "ok": False,
            "code": "missing_order_id",
            "message": "Order ID is required to check status.",
        }

    status_cycle = ["processing", "shipped", "delivered"]
    index = sum(ord(char) for char in order_id) % len(status_cycle)
    return {
        "ok": True,
        "code": "order_status",
        "order_id": order_id,
        "status": status_cycle[index],
    }


def change_booking(order_id: str | None, new_date: str | None) -> dict:
    if not order_id:
        return {
            "ok": False,
            "code": "missing_order_id",
            "message": "Order ID is required to change a booking.",
        }

    target_date = new_date or date.today().isoformat()
    return {
        "ok": True,
        "code": "booking_changed",
        "order_id": order_id,
        "new_date": target_date,
    }


def fallback_support() -> dict:
    return {
        "ok": True,
        "code": "fallback",
        "message": "A support specialist will review your request.",
    }


class MockBackendClient:
    def get_order_status(self, order_id: str | None) -> dict:
        return get_order_status(order_id)

    def change_booking(self, order_id: str | None, new_date: str | None) -> dict:
        return change_booking(order_id, new_date)

    def fallback_support(self) -> dict:
        return fallback_support()
