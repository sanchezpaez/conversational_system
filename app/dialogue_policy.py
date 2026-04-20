from app.models import EntityExtraction, IntentName

REQUIRED_FIELDS: dict[IntentName, list[str]] = {
    "order_status": ["order_id"],
    "change_booking": ["order_id", "date"],
    "fallback": [],
}


def get_missing_fields(intent: IntentName, entities: EntityExtraction) -> list[str]:
    missing: list[str] = []
    for field_name in REQUIRED_FIELDS[intent]:
        if not getattr(entities, field_name):
            missing.append(field_name)
    return missing


def build_clarification_reply(intent: IntentName, missing_fields: list[str]) -> str:
    if not missing_fields:
        return "Thanks, I have enough information to proceed."

    if missing_fields == ["order_id"]:
        if intent == "order_status":
            return "Happy to help! Could you share your order ID so I can check the status?"
        return "Of course! Could you share your order ID so I can update your booking?"

    if missing_fields == ["date"]:
        return "Almost there — what new date would you like? Please use YYYY-MM-DD if possible."

    if set(missing_fields) == {"order_id", "date"}:
        return "I'd be happy to help with that! Could you share your order ID and the new date (YYYY-MM-DD)?"

    missing_text = ", ".join(missing_fields)
    return f"To help you out, could you provide the following details: {missing_text}?"


ERROR_REPLIES: dict[str, str] = {
    "missing_order_id": (
        "I'd love to help, but I couldn't find an order ID in your message. "
        "Could you share it so I can look into this for you?"
    ),
    "fallback": (
        "I'm sorry I wasn't able to sort this out automatically. "
        "A support specialist will follow up with you shortly."
    ),
}

_DEFAULT_ERROR_REPLY = (
    "I'm sorry — something went wrong on our end. "
    "Please try again or reach out to support if the problem persists."
)


def build_error_reply(code: str) -> str:
    return ERROR_REPLIES.get(code, _DEFAULT_ERROR_REPLY)
