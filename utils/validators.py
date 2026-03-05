"""Input validators."""
import re


def validate_phone(phone: str) -> bool:
    """Validate phone number."""
    if not phone:
        return True
    cleaned = re.sub(r"\D", "", phone)
    return len(cleaned) >= 10


def validate_email(email: str) -> bool:
    """Validate email."""
    if not email:
        return True
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))
