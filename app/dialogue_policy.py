from app.models import EntityExtraction, IntentName, LanguageCode

REQUIRED_FIELDS: dict[IntentName, list[str]] = {
    "order_status": ["order_id"],
    "change_booking": ["order_id", "date"],
    "help": ["order_id"],
    "fallback": [],
}


def get_missing_fields(intent: IntentName, entities: EntityExtraction) -> list[str]:
    missing: list[str] = []
    for field_name in REQUIRED_FIELDS[intent]:
        if not getattr(entities, field_name):
            missing.append(field_name)
    return missing


_FIELD_LABELS: dict[LanguageCode, dict[str, str]] = {
    "en": {
        "order_id": "order ID",
        "date": "date",
    },
    "es": {
        "order_id": "ID del pedido",
        "date": "fecha",
    },
}


def build_clarification_reply(
    intent: IntentName,
    missing_fields: list[str],
    language: LanguageCode = "en",
) -> str:
    if not missing_fields:
        if language == "es":
            return "Gracias, ya tengo suficiente información para continuar."
        return "Thanks, I have enough information to proceed."

    if missing_fields == ["order_id"]:
        if intent == "order_status":
            if language == "es":
                return "¡Encantado de ayudar! ¿Puedes compartir el ID de tu pedido para que revise el estado?"
            return "Happy to help! Could you share your order ID so I can check the status?"
        if language == "es":
            return "¡Claro! ¿Puedes compartir el ID de tu pedido para que pueda actualizar tu reserva?"
        return "Of course! Could you share your order ID so I can update your booking?"

    if missing_fields == ["date"]:
        if language == "es":
            return "Ya casi está — ¿qué nueva fecha quieres? Si puedes, usa el formato YYYY-MM-DD."
        return "Almost there — what new date would you like? Please use YYYY-MM-DD if possible."

    if set(missing_fields) == {"order_id", "date"}:
        if language == "es":
            return "¡Con gusto te ayudo! ¿Puedes compartir el ID de tu pedido y la nueva fecha (YYYY-MM-DD)?"
        return "I'd be happy to help with that! Could you share your order ID and the new date (YYYY-MM-DD)?"

    missing_text = ", ".join(_FIELD_LABELS[language].get(field, field) for field in missing_fields)
    if language == "es":
        return f"Para ayudarte, ¿puedes facilitar estos datos: {missing_text}?"
    return f"To help you out, could you provide the following details: {missing_text}?"


ERROR_REPLIES: dict[LanguageCode, dict[str, str]] = {
    "en": {
        "missing_order_id": (
            "I'd love to help, but I couldn't find an order ID in your message. "
            "Could you share it so I can look into this for you?"
        ),
        "date_in_past": (
            "I can help with that — the requested date looks like it's in the past. "
            "Could you share a future date in YYYY-MM-DD format?"
        ),
        "fallback": (
            "I'm sorry I wasn't able to sort this out automatically. "
            "A support specialist will follow up with you shortly."
        ),
    },
    "es": {
        "missing_order_id": (
            "Me encantaría ayudarte, pero no encontré ningún ID de pedido en tu mensaje. "
            "¿Puedes compartirlo para que lo revise?"
        ),
        "date_in_past": (
            "Puedo ayudarte con eso, pero la fecha solicitada parece estar en el pasado. "
            "¿Puedes compartir una fecha futura en formato YYYY-MM-DD?"
        ),
        "fallback": (
            "Lo siento, no he podido resolver esto automáticamente. "
            "Un especialista de soporte revisará tu caso en breve."
        ),
    },
}

_DEFAULT_ERROR_REPLY: dict[LanguageCode, str] = {
    "en": (
        "I'm sorry — something went wrong on our end. "
        "Please try again or reach out to support if the problem persists."
    ),
    "es": (
        "Lo siento, algo salió mal de nuestro lado. "
        "Inténtalo de nuevo o contacta con soporte si el problema continúa."
    ),
}


def build_error_reply(code: str, language: LanguageCode = "en") -> str:
    return ERROR_REPLIES[language].get(code, _DEFAULT_ERROR_REPLY[language])
