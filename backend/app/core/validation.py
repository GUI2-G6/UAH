import re


EMAIL_PATTERN = re.compile(r"^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,63}$", re.IGNORECASE)
PHONE_ALLOWED_PATTERN = re.compile(r"^[0-9+\-().\s]+$")


def normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()


def require_valid_email(value: str | None, field_name: str = "email") -> str:
    normalized = normalize_email(value)
    if not normalized:
        raise ValueError(f"{field_name} is required")
    if not EMAIL_PATTERN.match(normalized):
        raise ValueError("Please enter a valid email address")
    return normalized


def normalize_phone(value: str | None) -> str | None:
    if value is None:
        return None

    raw = str(value).strip()
    if not raw:
        return None

    if not PHONE_ALLOWED_PATTERN.match(raw):
        raise ValueError("Please enter a valid phone number")

    has_plus = raw.lstrip().startswith("+")
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 7 or len(digits) > 15:
        raise ValueError("Please enter a valid phone number")

    if not has_plus:
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        if len(digits) == 11 and digits.startswith("1"):
            return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"

    if has_plus:
        return f"+{digits}"
    return digits
