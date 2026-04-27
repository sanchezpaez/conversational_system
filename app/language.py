import re

from app.models import LanguageCode

SPANISH_HINTS = {
    "hola",
    "pedido",
    "orden",
    "reserva",
    "cambiar",
    "fecha",
    "donde",
    "está",
    "esta",
    "quiero",
    "necesito",
    "ayuda",
    "gracias",
}

ENGLISH_HINTS = {
    "hello",
    "order",
    "booking",
    "change",
    "date",
    "where",
    "status",
    "please",
    "thanks",
    "help",
}


def detect_language(message: str, default_language: LanguageCode = "en") -> LanguageCode:
    text = message.strip().lower()
    if not text:
        return default_language

    spanish_score = 0
    english_score = 0

    if re.search(r"[áéíóúñ¿¡]", text):
        spanish_score += 2

    tokens = re.findall(r"[a-zA-Záéíóúñ]+", text)
    for token in tokens:
        if token in SPANISH_HINTS:
            spanish_score += 1
        if token in ENGLISH_HINTS:
            english_score += 1

    if spanish_score == english_score:
        return default_language
    if spanish_score > english_score:
        return "es"
    return "en"
