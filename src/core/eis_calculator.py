from decimal import Decimal, ROUND_HALF_UP

from .config_loader import get_config, parse_contribution_range
from .helper import CENTS, to_decimal


def calculate_eis(gross_salary) -> tuple[Decimal, Decimal]:
    """
    Calculates EIS employer and employee shares.

    Args:
        gross_salary: The total gross salary.

    Returns:
        tuple[Decimal, Decimal]: (employer_share, employee_share)
    """
    salary = to_decimal(gross_salary)
    if salary <= 0:
        return Decimal("0.00"), Decimal("0.00")

    eis_data = get_config("eis_contribution")
    if eis_data is None:
        raise FileNotFoundError("EIS contribution table not found in globally loaded configs.")

    for entry in eis_data:
        range_str = entry.get("amount_of_wages", "")
        matcher = parse_contribution_range(range_str)
        if matcher(salary):
            employer_share = to_decimal(entry.get("employer_contribution", 0.0))
            employee_share = to_decimal(entry.get("employee_contribution", 0.0))
            return employer_share.quantize(CENTS, rounding=ROUND_HALF_UP), employee_share.quantize(CENTS, rounding=ROUND_HALF_UP)

    # If no tier matched
    raise ValueError(f"No matching EIS tier found for wage RM {salary}")
