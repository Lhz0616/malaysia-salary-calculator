from decimal import Decimal, ROUND_HALF_UP

from .config_loader import get_config, parse_contribution_range
from .helper import CENTS, to_decimal


def calculate_epf(epf_eligible_salary, category: str = "first_category") -> tuple[Decimal, Decimal]:
    """
    Calculates employee and employer EPF contributions.

    Args:
        epf_eligible_salary: The wages subject to EPF (Basic Salary + Additional Income - Deductions).
        category (str): Either 'first_category' or 'second_category'.

    Returns:
        tuple[Decimal, Decimal]: (employee_epf, employer_epf)
    """
    # Load epf table from globally loaded configs
    epf_data = get_config("epf_contribution_rates")
    if epf_data is None:
        raise FileNotFoundError("EPF contribution table not found in globally loaded configs.")

    category_data = epf_data['categoryA'] if category == "first_category" else epf_data['categoryB']
    epf_rates = category_data.get("rates", [])

    salary = to_decimal(epf_eligible_salary)

    if salary > Decimal("20000"):
        if category == "first_category":
            employee_share = (salary * Decimal("0.11")).quantize(CENTS, rounding=ROUND_HALF_UP)
            employer_share = (salary * Decimal("0.12")).quantize(CENTS, rounding=ROUND_HALF_UP)
            return employee_share, employer_share
        else:
            return Decimal("0.00"), (salary * Decimal("0.04")).quantize(CENTS, rounding=ROUND_HALF_UP)
    elif salary <= Decimal("0"):
        return Decimal("0.00"), Decimal("0.00")

    for entry in epf_rates:
        range_str = entry.get("range", "")
        matcher = parse_contribution_range(range_str)
        if matcher(salary):
            employer_share = to_decimal(entry.get("employer_contribution", 0))
            employee_share = to_decimal(entry.get("employee_contribution", 0))

            return employee_share.quantize(CENTS, rounding=ROUND_HALF_UP), employer_share.quantize(CENTS, rounding=ROUND_HALF_UP)

    # If not tier matched
    raise ValueError(f"No matching EPF tier found for wage RM {salary}")
