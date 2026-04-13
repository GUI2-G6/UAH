import re


EMAIL_PATTERN = re.compile(r"^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,63}$", re.IGNORECASE)
PHONE_ALLOWED_PATTERN = re.compile(r"^[0-9+\-().\s]+$")
PHONE_COUNTRY_CODES = (
    {"prefix": "1", "code": "US", "label": "United States"},
    {"prefix": "44", "code": "GB", "label": "United Kingdom"},
    {"prefix": "49", "code": "DE", "label": "Germany"},
    {"prefix": "61", "code": "AU", "label": "Australia"},
    {"prefix": "81", "code": "JP", "label": "Japan"},
    {"prefix": "91", "code": "IN", "label": "India"},
)


def _phone_parts(value: str | None) -> tuple[str, bool]:
    raw = str(value or "").strip()
    if not raw:
        return "", False

    if not PHONE_ALLOWED_PATTERN.match(raw):
        raise ValueError("Please enter a valid phone number")

    has_plus = raw.startswith("+")
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 7 or len(digits) > 15:
        raise ValueError("Please enter a valid phone number")

    return digits, has_plus


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

    digits, has_plus = _phone_parts(value)
    if not digits:
        return None

    if not has_plus:
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        if len(digits) == 11 and digits.startswith("1"):
            return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"

    if has_plus:
        return f"+{digits}"
    return digits


def build_mailto_href(value: str | None) -> str:
    normalized = normalize_email(value)
    if not normalized or not EMAIL_PATTERN.match(normalized):
        return ""
    return f"mailto:{normalized}"


def build_phone_href(value: str | None) -> str:
    try:
        normalized = normalize_phone(value)
    except ValueError:
        return ""

    if not normalized:
        return ""

    if normalized.startswith("+"):
        return f"tel:{normalized}"

    digits = re.sub(r"\D", "", normalized)
    if len(digits) == 10:
        return f"tel:+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"tel:+{digits}"
    return f"tel:{digits}"


def infer_phone_country(value: str | None) -> dict[str, str] | None:
    try:
        digits, has_plus = _phone_parts(value)
    except ValueError:
        return None

    if not digits:
        return None

    if not has_plus:
        if len(digits) == 10 or (len(digits) == 11 and digits.startswith("1")):
            return {"code": "US", "label": "United States"}
        return None

    for candidate in PHONE_COUNTRY_CODES:
        if digits.startswith(candidate["prefix"]):
            return {"code": candidate["code"], "label": candidate["label"]}

    return None
