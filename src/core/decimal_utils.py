from decimal import Decimal

# Shared quantization precision targets
CENTS = Decimal("0.01")
FOUR_PLACES = Decimal("0.0001")


def to_decimal(value, default="0.00") -> Decimal:
    """Build a Decimal safely from string, int, float, or None."""
    if value is None:
        return Decimal(str(default))
    if isinstance(value, Decimal):
        return value
    s = str(value).strip().replace(",", "")
    if not s or s.upper() == "N/A":
        return Decimal(str(default))
    try:
        return Decimal(s)
    except Exception:
        return Decimal(str(default))
