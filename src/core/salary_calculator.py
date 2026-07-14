from decimal import ROUND_HALF_UP
import calendar
from .config_loader import get_configs
from .epf_calculator import calculate_epf
from .socso_calculator import calculate_socso
from .eis_calculator import calculate_eis
from .pcb_calculator import calculate_pcb
from .helper import CENTS, to_decimal

def calculate_salary_package(
    monthly_salary: float = 0.0,
    overtime_weekday_hours: float = 0.0,
    overtime_weekend_hours: float = 0.0,
    overtime_holiday_hours: float = 0.0,
    late_hours: float = 0.0,
    unpaid_leave_days: float = 0.0,
    taxable_additional_income: float = 0.0,
    nontaxable_additional_income: float = 0.0,
    socso_category: str = "first_category",
    include_non_employment_injury: bool = False,
    spouse_eligible: bool = False,
    children_count: int = 0,
    marital_status: str = "Single",
    month: int = 7,
    year: int = 2026,
    is_part_timer: bool = False,
    total_working_hours: float = 0.0,
    hourly_rate: float = 0.0
) -> dict:
    """
    Executes the master payroll calculation pipeline.
    
    When is_part_timer is True, a simplified calculation is returned:
    nett = total_working_hours * hourly_rate + additional_income (no statutory deductions).
    
    Returns:
        dict: Containing all breakdown items for inputs, additions, deductions,
              statutory contributions (employee + employer shares), and final nett salary.
    """
    # --- Part-timer shortcut ---
    if is_part_timer:
        nett = float(total_working_hours) * float(hourly_rate) + float(taxable_additional_income)
        return {
            "is_part_timer": True,
            "nett_salary": round(nett, 2),
            "gross_salary": round(nett, 2),
            "inputs": {
                "total_working_hours": total_working_hours,
                "hourly_rate": hourly_rate,
                "taxable_additional_income": round(taxable_additional_income, 2),
                "month": month,
                "year": year
            }
        }

    # 1. Load config (global data configs loaded once here, calculators refer to them)
    configs = get_configs()
    config = configs.get("config", {})
    
    # Extract config parameters
    fixed_overtime_days = float(config.get("fixed_overtime_days", 26))
    overtime_rates = config.get("overtime_rates", {
        "weekday": 1.5,
        "weekend": 2.0,
        "public_holiday": 3.0
    })
    
    # Resolve dynamic calendar days if configured
    def resolve_days_param(config_val, fallback):
        if config_val == "calendar_days":
            return calendar.monthrange(year, month)[1]
        try:
            return float(config_val)
        except (ValueError, TypeError):
            return fallback

    unpaid_leave_days_config = config.get("fixed_unpaid_leave_days", "calendar_days")
    late_hours_days_config = config.get("fixed_late_hours_days", "calendar_days")

    unpaid_leave_days_val = resolve_days_param(unpaid_leave_days_config, fixed_overtime_days)
    late_hours_days_val = resolve_days_param(late_hours_days_config, fixed_overtime_days)
    
    # 2. Hourly rate calculations
    # Overtime hourly rate (uses fixed_overtime_days) - normal value
    if fixed_overtime_days > 0:
        hourly_rate_ot = float(monthly_salary) / (fixed_overtime_days * 8.0)
    else:
        hourly_rate_ot = 0.0

    # Late deduction hourly rate (uses late_hours_days_val) - uses to_decimal()
    if late_hours_days_val > 0:
        hourly_rate_late = (to_decimal(monthly_salary) / to_decimal(late_hours_days_val * 8.0)).quantize(CENTS, ROUND_HALF_UP)
    else:
        hourly_rate_late = to_decimal(0)

    # Unpaid leave daily rate (uses unpaid_leave_days_val) - uses to_decimal()
    if unpaid_leave_days != 0 and unpaid_leave_days % 8 == 0:
        unpaid_leave_rate = (to_decimal(monthly_salary) / to_decimal(unpaid_leave_days_val)).quantize(CENTS, ROUND_HALF_UP)
        unpaid_leave_days = int(unpaid_leave_days / 8)
    elif unpaid_leave_days > 0:
        unpaid_leave_rate = (to_decimal(monthly_salary) / to_decimal(unpaid_leave_days_val * 8.0)).quantize(CENTS, ROUND_HALF_UP)
    else:
        unpaid_leave_rate = to_decimal(0)

    # 3. Overtime Pay (normal values)
    weekday_rate = overtime_rates.get("weekday", 1.5)
    weekend_rate = overtime_rates.get("weekend", 2.0)
    holiday_rate = overtime_rates.get("public_holiday", 3.0)

    overtime_weekday_pay = float(overtime_weekday_hours) * hourly_rate_ot * float(weekday_rate)
    overtime_weekend_pay = float(overtime_weekend_hours) * hourly_rate_ot * float(weekend_rate)
    overtime_holiday_pay = float(overtime_holiday_hours) * hourly_rate_ot * float(holiday_rate)
    total_overtime_pay = overtime_weekday_pay + overtime_weekend_pay + overtime_holiday_pay

    # 4. Deductions - the two deduction amounts use to_decimal()
    late_deduction = (to_decimal(hourly_rate_late) * to_decimal(late_hours)).quantize(CENTS, ROUND_HALF_UP)
    unpaid_leave_deduction = (to_decimal(unpaid_leave_rate) * to_decimal(unpaid_leave_days)).quantize(CENTS, ROUND_HALF_UP)
    late_deduction = float(late_deduction)
    unpaid_leave_deduction = float(unpaid_leave_deduction)
    total_deductions = late_deduction + unpaid_leave_deduction

    # 5. Gross Salary (normal value)
    gross_salary = float(monthly_salary) + total_overtime_pay + float(taxable_additional_income) - total_deductions
    if gross_salary < 0.0:
        gross_salary = 0.0

    # 6. EPF Calculation
    epf_eligible_salary = float(monthly_salary) + float(taxable_additional_income) - total_deductions
    if epf_eligible_salary < 0.0:
        epf_eligible_salary = 0.0
    epf_employee, epf_employer = calculate_epf(epf_eligible_salary, category=socso_category)
    epf_employee, epf_employer = float(epf_employee), float(epf_employer)

    # 7. SOCSO Calculation
    socso_employer, socso_employee = calculate_socso(gross_salary, socso_category, include_non_employment_injury)
    socso_employer, socso_employee = float(socso_employer), float(socso_employee)

    # 8. EIS Calculation
    eis_employer, eis_employee = calculate_eis(gross_salary)
    eis_employer, eis_employee = float(eis_employer), float(eis_employee)

    # 9. PCB Calculation
    pcb_amount = calculate_pcb(
        gross_salary=gross_salary,
        epf_employee=epf_employee,
        spouse_eligible=spouse_eligible,
        children_count=children_count,
        pcb_config=config.get("pcb", {})
    )
    pcb_amount = float(pcb_amount)
    
    # 10. Nett Salary
    nett_salary = gross_salary - epf_employee - socso_employee - eis_employee - pcb_amount + float(nontaxable_additional_income)
    if nett_salary < 0.0:
        nett_salary = 0.0
        
    return {
        "inputs": {
            "monthly_salary": round(monthly_salary, 2),
            "overtime_weekday_hours": overtime_weekday_hours,
            "overtime_weekend_hours": overtime_weekend_hours,
            "overtime_holiday_hours": overtime_holiday_hours,
            "late_hours": late_hours,
            "unpaid_leave_days": unpaid_leave_days,
            "taxable_additional_income": round(taxable_additional_income, 2),
            "nontaxable_additional_income": round(nontaxable_additional_income, 2),
            "socso_category": socso_category,
            "spouse_eligible": spouse_eligible,
            "children_count": children_count,
            "marital": marital_status,
            "month": month,
            "year": year
        },
        "rates": {
            "hourly_rate": round(hourly_rate_ot, 4),
            "hourly_rate_ot": round(hourly_rate_ot, 4),
            "hourly_rate_late": round(hourly_rate_late, 4),
            "unpaid_leave_rate": round(unpaid_leave_rate, 4)
        },
        "additions": {
            "overtime_weekday_pay": round(overtime_weekday_pay, 2),
            "overtime_weekend_pay": round(overtime_weekend_pay, 2),
            "overtime_holiday_pay": round(overtime_holiday_pay, 2),
            "total_overtime_pay": round(total_overtime_pay, 2),
            "taxable_additional_income": round(taxable_additional_income, 2),
            "nontaxable_additional_income": round(nontaxable_additional_income, 2)
        },
        "deductions": {
            "late_deduction": round(late_deduction, 2),
            "unpaid_leave_deduction": round(unpaid_leave_deduction, 2),
            "total_deductions": round(total_deductions, 2)
        },
        "gross_salary": round(gross_salary, 2),
        "statutory": {
            "epf_employee": round(epf_employee, 2),
            "epf_employer": round(epf_employer, 2),
            "socso_employee": round(socso_employee, 2),
            "socso_employer": round(socso_employer, 2),
            "eis_employee": round(eis_employee, 2),
            "eis_employer": round(eis_employer, 2),
            "pcb": round(pcb_amount, 2)
        },
        "nett_salary": round(nett_salary, 2)
    }
