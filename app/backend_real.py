import json
from urllib import error, request

from app import backend


class RealBackendClient:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def get_order_status(self, order_id: str | None) -> dict:
        if not order_id:
            return {
                "ok": False,
                "code": "missing_order_id",
                "message": "Order ID is required to check status.",
            }

        payload = self._post_json("/order-status", {"order_id": order_id})
        if not payload.get("ok", False):
            return payload

        return {
            "ok": True,
            "code": "order_status",
            "order_id": payload.get("order_id", order_id),
            "status": payload.get("status", "processing"),
        }

    def change_booking(self, order_id: str | None, new_date: str | None) -> dict:
        if not order_id:
            return {
                "ok": False,
                "code": "missing_order_id",
                "message": "Order ID is required to change a booking.",
            }

        payload = self._post_json(
            "/change-booking",
            {"order_id": order_id, "new_date": new_date},
        )
        if not payload.get("ok", False):
            return payload

        return {
            "ok": True,
            "code": "booking_changed",
            "order_id": payload.get("order_id", order_id),
            "new_date": payload.get("new_date", new_date),
        }

    def fallback_support(self) -> dict:
        return backend.fallback_support()

    def _post_json(self, path: str, payload: dict) -> dict:
        url = f"{self.base_url}{path}"
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        req = request.Request(url=url, data=body, headers=headers, method="POST")

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                data = response.read().decode("utf-8")
            parsed = json.loads(data)
            if isinstance(parsed, dict):
                return parsed
            return self._unavailable_response("invalid_backend_payload")
        except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError):
            return self._unavailable_response("backend_unavailable")

    def _unavailable_response(self, code: str) -> dict:
        return {
            "ok": False,
            "code": code,
            "message": "Backend service is unavailable.",
        }
