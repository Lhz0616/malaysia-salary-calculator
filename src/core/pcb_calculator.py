import os
from decimal import Decimal, ROUND_HALF_UP

from .config_loader import get_config
from .helper import CENTS, to_decimal


def parse_pcb_bracket(bracket_str: str) -> tuple[Decimal, Decimal | None]:
    """
    Parses bracket range string like '>=0;<=5000', '>5000;<=20000', '>2000000'.
    Returns (lower_bound, upper_bound).
    """
    parts = bracket_str.split(';')
    lower = Decimal("0")
    upper = None

    for part in parts:
        part = part.strip()
        if part.startswith(">="):
            lower = Decimal(part[2:])
        elif part.startswith(">"):
            lower = Decimal(part[1:])
        elif part.startswith("<="):
            upper = Decimal(part[2:])
        elif part.startswith("<"):
            upper = Decimal(part[1:])

    return lower, upper


def calculate_pcb(
    gross_salary,
    epf_employee,
    spouse_eligible: bool,
    children_count: int,
    pcb_config: dict
) -> Decimal:
    """
    Calculates the Monthly Tax Deduction (PCB).

    Args:
        gross_salary: The total monthly gross salary.
        epf_employee: Monthly employee EPF contribution.
        spouse_eligible (bool): Whether eligible for spouse tax relief.
        children_count (int): Number of children.
        pcb_config (dict): The "pcb" section of config.json.

    Returns:
        Decimal: Monthly tax deduction (PCB) quantized to 2 decimal places.
    """
    gross = to_decimal(gross_salary)
    epf_emp = to_decimal(epf_employee)

    # 1. Annualize income
    annual_income = gross * 12

    # 2. Annualize EPF contribution
    annual_epf = epf_emp * 12

    # 3. Apply Reliefs (EPF is included as a relief, capped at config max)
    reliefs = pcb_config.get("reliefs", {})
    self_relief = to_decimal(reliefs.get("self", 9000.0))
    spouse_relief = to_decimal(reliefs.get("spouse", 4000.0)) if spouse_eligible else Decimal("0")
    child_relief = to_decimal(reliefs.get("child", 2000.0))
    epf_relief_cap = to_decimal(reliefs.get("epf", 4000.0))

    # EPF relief is the lesser of actual annual EPF or the configured cap
    epf_relief = min(annual_epf, epf_relief_cap)

    total_relief = self_relief + spouse_relief + (child_relief * children_count) + epf_relief

    # 4. Chargeable Income
    chargeable_income = annual_income - total_relief

    # If chargeable income is zero, negative or lower than the minimum (RM37,333 as of 2026)
    if chargeable_income <= 37333:
        return Decimal("0.00")

    # 5. Progressive Tax Bracket search
    brackets_rel_path = pcb_config.get("tax_brackets_file", "src/data/income_tax_bracket_2025.json")
    # Derive the file stem (e.g. 'income_tax_bracket_2025') and read from global configs
    brackets_stem = os.path.splitext(os.path.basename(brackets_rel_path))[0]
    brackets = get_config(brackets_stem)
    if brackets is None:
        raise FileNotFoundError(f"Tax brackets '{brackets_stem}' not found in globally loaded configs.")

    annual_tax = Decimal("0")
    bracket_matched = False

    for bracket in brackets:
        lower, upper = parse_pcb_bracket(bracket["Chargeable Income"])

        # Check if income falls inside this tier
        if chargeable_income > lower and (upper is None or chargeable_income <= upper):
            # Parse previous tax total, handles commas like "1,500"
            prev_total_str = str(bracket["previous tax total"]).replace(",", "")
            previous_tax_total = Decimal(prev_total_str)
            rate = Decimal(str(bracket["Rate"]))

            taxable_amount_in_this_bracket = chargeable_income - lower
            annual_tax = previous_tax_total + (taxable_amount_in_this_bracket * rate)
            bracket_matched = True
            break

    if not bracket_matched:
        raise ValueError(f"No matching tax bracket found for chargeable income RM {chargeable_income}")

    # 6. Monthly PCB
    pcb = annual_tax / 12

    return pcb.quantize(CENTS, rounding=ROUND_HALF_UP)
