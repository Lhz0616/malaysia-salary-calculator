from decimal import Decimal

# Shared quantization targets
CENTS = Decimal("0.01")
FOUR_PLACES = Decimal("0.0001")


def to_decimal(value) -> Decimal:
    """Build a Decimal from a string (never directly from a float)."""
    return Decimal(str(value))
