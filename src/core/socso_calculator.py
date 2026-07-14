from decimal import Decimal, ROUND_HALF_UP

from .config_loader import get_config, parse_contribution_range
from .helper import CENTS, to_decimal


def calculate_socso(gross_salary, category: str = "first_category", include_non_employment_injury: bool = False) -> tuple[Decimal, Decimal]:
    """
    Calculates SOCSO employer and employee shares.

    Args:
        gross_salary: The total gross salary.
        category (str): Either 'first_category' (under 60) or 'second_category' (60 and above).
        include_non_employment_injury (bool): When True, the employee share includes both
            the invalidity and the non-employment injury portions. When False, only the
            invalidity portion is counted.

    Returns:
        tuple[Decimal, Decimal]: (employer_share, employee_share)
    """
    salary = to_decimal(gross_salary)
    if salary <= 0:
        return Decimal("0.00"), Decimal("0.00")

    # Load socso table from globally loaded configs
    socso_data = get_config("socso_contribution")
    if socso_data is None:
        raise FileNotFoundError("SOCSO contribution table not found in globally loaded configs.")

    for entry in socso_data:
        range_str = entry.get("monthly_salary", "")
        matcher = parse_contribution_range(range_str)
        if matcher(salary):
            # Matched a tier
            cat_data = entry.get(category)
            if not cat_data:
                raise ValueError(f"Category '{category}' not found in matched SOCSO tier '{range_str}'")

            employer_share = to_decimal(cat_data.get("employer_share", 0.0))

            invalidity = to_decimal(cat_data.get("employee_share_invalidity", 0.0))
            injury = to_decimal(cat_data.get("employee_share_non_employment_injury", 0.0))

            # Base employee share is always the invalidity portion.
            employee_share = invalidity
            # Add the non-employment injury portion only when the scheme applies.
            if include_non_employment_injury:
                employee_share += injury

            return employer_share.quantize(CENTS, rounding=ROUND_HALF_UP), employee_share.quantize(CENTS, rounding=ROUND_HALF_UP)

    # If no tier matched
    raise ValueError(f"No matching SOCSO tier found for wage RM {salary}")
