import sqlite3
from datetime import date
from pathlib import Path
from typing import Protocol

from app.config import get_orders_db_path


DEFAULT_ORDERS = [
    ("AB-123", "Ana García", "processing", "2026-09-12"),
    ("7821", "Luis Pérez", "shipped", "2026-09-16"),
    ("CX-440", "Marta Silva", "delivered", "2026-08-30"),
    ("PT-900", "David Chen", "processing", "2026-09-17"),
    ("WO-204", "Sofia Rossi", "shipped", "2026-09-18"),
    ("LM-771", "Nora Ahmed", "delivered", "2026-08-25"),
    ("VY-120", "Pablo Moreno", "processing", "2026-09-15"),
    ("RR-654", "Emma Dubois", "shipped", "2026-09-14"),
    ("QZ-989", "Jonas Becker", "delivered", "2026-08-27"),
    ("TR-118", "Laura Novak", "processing", "2026-09-20"),
]


class BackendClient(Protocol):
    def get_order_status(self, order_id: str | None) -> dict:
        ...

    def change_booking(self, order_id: str | None, new_date: str | None) -> dict:
        ...

    def fallback_support(self) -> dict:
        ...


def _normalize_order_id(order_id: str | None) -> str | None:
    if order_id is None:
        return None

    normalized = str(order_id).strip()
    return normalized.upper() if normalized else None


def _get_orders_connection(db_path: str | None = None) -> sqlite3.Connection:
    resolved_path = Path(db_path or get_orders_db_path())
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(resolved_path)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL UNIQUE,
            customer_name TEXT NOT NULL,
            status TEXT NOT NULL,
            booking_date TEXT NOT NULL
        )
        """
    )

    row_count = connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    if row_count == 0:
        connection.executemany(
            "INSERT INTO orders (order_id, customer_name, status, booking_date) VALUES (?, ?, ?, ?)",
            DEFAULT_ORDERS,
        )
        connection.commit()

    return connection


class MockBackendClient:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or get_orders_db_path()

    def _load_order(self, order_id: str | None) -> sqlite3.Row | None:
        normalized_order_id = _normalize_order_id(order_id)
        if not normalized_order_id:
            return None

        with _get_orders_connection(self.db_path) as connection:
            return connection.execute(
                "SELECT order_id, customer_name, status, booking_date FROM orders WHERE order_id = ?",
                (normalized_order_id,),
            ).fetchone()

    def get_order_status(self, order_id: str | None) -> dict:
        normalized_order_id = _normalize_order_id(order_id)
        if not normalized_order_id:
            return {
                "ok": False,
                "code": "missing_order_id",
                "message": "Order ID is required to check status.",
            }

        with _get_orders_connection(self.db_path) as connection:
            row = connection.execute(
                "SELECT order_id, customer_name, status, booking_date FROM orders WHERE order_id = ?",
                (normalized_order_id,),
            ).fetchone()

        if row is not None:
            return {
                "ok": True,
                "code": "order_status",
                "order_id": row["order_id"],
                "customer_name": row["customer_name"],
                "status": row["status"],
                "booking_date": row["booking_date"],
            }

        status_cycle = ["processing", "shipped", "delivered"]
        index = sum(ord(char) for char in normalized_order_id) % len(status_cycle)
        return {
            "ok": True,
            "code": "order_status",
            "order_id": normalized_order_id,
            "status": status_cycle[index],
        }

    def change_booking(self, order_id: str | None, new_date: str | None) -> dict:
        normalized_order_id = _normalize_order_id(order_id)
        if not normalized_order_id:
            return {
                "ok": False,
                "code": "missing_order_id",
                "message": "Order ID is required to change a booking.",
            }

        target_date = new_date or date.today().isoformat()

        with _get_orders_connection(self.db_path) as connection:
            row = connection.execute(
                "SELECT order_id FROM orders WHERE order_id = ?",
                (normalized_order_id,),
            ).fetchone()
            if row is not None:
                connection.execute(
                    "UPDATE orders SET booking_date = ? WHERE order_id = ?",
                    (target_date, normalized_order_id),
                )
                connection.commit()
                return {
                    "ok": True,
                    "code": "booking_changed",
                    "order_id": normalized_order_id,
                    "new_date": target_date,
                }

        return {
            "ok": True,
            "code": "booking_changed",
            "order_id": normalized_order_id,
            "new_date": target_date,
        }

    def fallback_support(self) -> dict:
        return {
            "ok": True,
            "code": "fallback",
            "message": "A support specialist will review your request.",
        }


def get_order_status(order_id: str | None) -> dict:
    return MockBackendClient().get_order_status(order_id)


def change_booking(order_id: str | None, new_date: str | None) -> dict:
    return MockBackendClient().change_booking(order_id, new_date)


def fallback_support() -> dict:
    return MockBackendClient().fallback_support()
