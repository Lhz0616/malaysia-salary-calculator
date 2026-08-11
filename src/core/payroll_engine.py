import calendar
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from .config_loader import get_configs
from .decimal_utils import CENTS, to_decimal


@dataclass(frozen=True)
class PayrollInput:
    monthly_salary: Decimal = Decimal("0.00")
    overtime_weekday_hours: Decimal = Decimal("0.00")
    overtime_weekend_hours: Decimal = Decimal("0.00")
    overtime_holiday_hours: Decimal = Decimal("0.00")
    late_hours: Decimal = Decimal("0.00")
    unpaid_leave_days: Decimal = Decimal("0.00")
    taxable_additional_income: Decimal = Decimal("0.00")
    nontaxable_additional_income: Decimal = Decimal("0.00")
    socso_category: str = "first_category"
    include_non_employment_injury: bool = False
    spouse_eligible: bool = False
    children_count: int = 0
    marital_status: str = "Single"
    month: int = 7
    year: int = 2026
    is_part_timer: bool = False
    total_working_hours: Decimal = Decimal("0.00")
    hourly_rate: Decimal = Decimal("0.00")

    @classmethod
    def from_dict(cls, data: dict) -> "PayrollInput":
        """Convenience factory to create PayrollInput from raw float/int/str dict values."""
        return cls(
            monthly_salary=to_decimal(data.get("monthly_salary", 0.0)),
            overtime_weekday_hours=to_decimal(data.get("overtime_weekday_hours", 0.0)),
            overtime_weekend_hours=to_decimal(data.get("overtime_weekend_hours", 0.0)),
            overtime_holiday_hours=to_decimal(data.get("overtime_holiday_hours", 0.0)),
            late_hours=to_decimal(data.get("late_hours", 0.0)),
            unpaid_leave_days=to_decimal(data.get("unpaid_leave_days", 0.0)),
            taxable_additional_income=to_decimal(
                data.get("taxable_additional_income", 0.0)
            ),
            nontaxable_additional_income=to_decimal(
                data.get("nontaxable_additional_income", 0.0)
            ),
            socso_category=str(data.get("socso_category", "first_category")),
            include_non_employment_injury=bool(
                data.get("include_non_employment_injury", False)
            ),
            spouse_eligible=bool(data.get("spouse_eligible", False)),
            children_count=int(data.get("children_count", 0)),
            marital_status=str(data.get("marital_status", "Single")),
            month=int(data.get("month", 7)),
            year=int(data.get("year", 2026)),
            is_part_timer=bool(data.get("is_part_timer", False)),
            total_working_hours=to_decimal(data.get("total_working_hours", 0.0)),
            hourly_rate=to_decimal(data.get("hourly_rate", 0.0)),
        )


@dataclass(frozen=True)
class RateInterval:
    lower_bound: Decimal
    upper_bound: Decimal | None  # None means infinity
    employee_share: Decimal
    employer_share: Decimal
    extra_data: dict = field(default_factory=dict)

    def matches(self, val: Decimal) -> bool:
        if val < self.lower_bound:
            return False
        if self.upper_bound is not None and val > self.upper_bound:
            return False
        return True

def parse_interval(range_str: str) -> tuple[Decimal, Decimal | None]:
    """
    Parses expressions like '<=30', '>30;<=50', '>6000', '>=0;<=5000'.
    Returns (lower_inclusive_or_exclusive_bound, upper_bound_or_None).
    """
    parts = range_str.split(";")
    lower = Decimal("0.00")
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


class StatutoryRateRepository:
    """
    Pre-compiles statutory JSON data into structured numeric interval tables for high-performance,
    isolated lookups without repetitive string parsing.
    """

    def __init__(self, configs: dict):
        self.epf_cat_a: list[RateInterval] = self._build_epf_intervals(
            configs, "categoryA"
        )
        self.epf_cat_b: list[RateInterval] = self._build_epf_intervals(
            configs, "categoryB"
        )
        self.socso_intervals: list[RateInterval] = self._build_socso_intervals(configs)
        self.eis_intervals: list[RateInterval] = self._build_eis_intervals(configs)
        self.pcb_brackets: list[dict] = configs.get("income_tax_bracket_2025", [])
        self.config: dict = configs.get("config", {})

    def _build_epf_intervals(
        self, configs: dict, category_key: str
    ) -> list[RateInterval]:
        epf_data = configs.get("epf_contribution_rates", {})
        cat_data = epf_data.get(category_key, {})
        rates = cat_data.get("rates", [])
        intervals = []
        for entry in rates:
            lower, upper = parse_interval(entry.get("range", ""))
            intervals.append(
                RateInterval(
                    lower_bound=lower,
                    upper_bound=upper,
                    employee_share=to_decimal(entry.get("employee_contribution", 0)),
                    employer_share=to_decimal(entry.get("employer_contribution", 0)),
                )
            )
        return intervals

    def _build_socso_intervals(self, configs: dict) -> list[RateInterval]:
        socso_data = configs.get("socso_contribution", [])
        intervals = []
        for entry in socso_data:
            lower, upper = parse_interval(entry.get("monthly_salary", ""))
            intervals.append(
                RateInterval(
                    lower_bound=lower,
                    upper_bound=upper,
                    employee_share=Decimal("0.00"),
                    employer_share=Decimal("0.00"),
                    extra_data=entry,
                )
            )
        return intervals

    def _build_eis_intervals(self, configs: dict) -> list[RateInterval]:
        eis_data = configs.get("eis_contribution", [])
        intervals = []
        for entry in eis_data:
            lower, upper = parse_interval(entry.get("amount_of_wages", ""))
            intervals.append(
                RateInterval(
                    lower_bound=lower,
                    upper_bound=upper,
                    employee_share=to_decimal(entry.get("employee_contribution", 0)),
                    employer_share=to_decimal(entry.get("employer_contribution", 0)),
                )
            )
        return intervals


class PayrollEngine:
    """
    Deep domain module implementing the Malaysian payroll computation pipeline.
    Encapsulates rate table lookups, exact Decimal calculations, overtime pay,
    unpaid leave, late deductions, and statutory contributions (EPF, SOCSO, EIS, PCB).
    """

    def __init__(self, repo: StatutoryRateRepository | None = None):
        if repo is None:
            configs = get_configs()
            repo = StatutoryRateRepository(configs)
        self.repo = repo

    @classmethod
    def default(cls) -> "PayrollEngine":
        return cls(StatutoryRateRepository(get_configs()))

    def calculate(self, inp: PayrollInput) -> dict:
        """Executes full payroll calculation and returns structured breakdown dict."""
        if inp.is_part_timer:
            nett = (
                inp.total_working_hours * inp.hourly_rate
            ) + inp.taxable_additional_income
            nett_val = float(nett.quantize(CENTS, ROUND_HALF_UP))
            return {
                "is_part_timer": True,
                "nett_salary": nett_val,
                "gross_salary": nett_val,
                "inputs": {
                    "total_working_hours": float(inp.total_working_hours),
                    "hourly_rate": float(inp.hourly_rate),
                    "taxable_additional_income": float(inp.taxable_additional_income),
                    "month": inp.month,
                    "year": inp.year,
                },
            }

        config = self.repo.config
        fixed_overtime_days = to_decimal(config.get("fixed_overtime_days", 26))
        overtime_rates = config.get(
            "overtime_rates", {"weekday": 1.5, "weekend": 2.0, "public_holiday": 3.0}
        )

        # Resolve days parameter
        def resolve_days(config_val, fallback: Decimal) -> Decimal:
            if config_val == "calendar_days":
                return Decimal(calendar.monthrange(inp.year, inp.month)[1])
            try:
                return to_decimal(config_val)
            except Exception:
                return fallback

        unpaid_days_val = resolve_days(
            config.get("fixed_unpaid_leave_days", "calendar_days"), fixed_overtime_days
        )
        late_days_val = resolve_days(
            config.get("fixed_late_hours_days", "calendar_days"), fixed_overtime_days
        )

        # 1. Hourly & Daily rates
        hourly_rate_ot = (
            (inp.monthly_salary / (fixed_overtime_days * Decimal("8.0")))
            if fixed_overtime_days > 0
            else Decimal(0)
        )
        hourly_rate_late = (
            (inp.monthly_salary / (late_days_val * Decimal("8.0"))).quantize(
                CENTS, ROUND_HALF_UP
            )
            if late_days_val > 0
            else Decimal(0)
        )

        if inp.unpaid_leave_days != 0 and inp.unpaid_leave_days % 8 == 0:
            unpaid_leave_rate = (inp.monthly_salary / unpaid_days_val).quantize(
                CENTS, ROUND_HALF_UP
            )
            effective_unpaid_days = inp.unpaid_leave_days / Decimal(8)
        elif inp.unpaid_leave_days > 0:
            unpaid_leave_rate = (
                inp.monthly_salary / (unpaid_days_val * Decimal("8.0"))
            ).quantize(CENTS, ROUND_HALF_UP)
            effective_unpaid_days = inp.unpaid_leave_days
        else:
            unpaid_leave_rate = Decimal(0)
            effective_unpaid_days = Decimal(0)

        # 2. Overtime Pay
        wkday_mult = to_decimal(overtime_rates.get("weekday", 1.5))
        wkend_mult = to_decimal(overtime_rates.get("weekend", 2.0))
        hol_mult = to_decimal(overtime_rates.get("public_holiday", 3.0))

        ot_weekday_pay = inp.overtime_weekday_hours * hourly_rate_ot * wkday_mult
        ot_weekend_pay = inp.overtime_weekend_hours * hourly_rate_ot * wkend_mult
        ot_holiday_pay = inp.overtime_holiday_hours * hourly_rate_ot * hol_mult
        total_ot_pay = ot_weekday_pay + ot_weekend_pay + ot_holiday_pay

        # 3. Deductions
        late_deduction = (hourly_rate_late * inp.late_hours).quantize(
            CENTS, ROUND_HALF_UP
        )
        unpaid_leave_deduction = (unpaid_leave_rate * effective_unpaid_days).quantize(
            CENTS, ROUND_HALF_UP
        )
        total_deductions = late_deduction + unpaid_leave_deduction

        # 4. Gross Salary
        gross_salary = (
            inp.monthly_salary
            + total_ot_pay
            + inp.taxable_additional_income
            - total_deductions
        )
        if gross_salary < Decimal(0):
            gross_salary = Decimal("0.00")

        # 5. EPF
        epf_eligible = (
            inp.monthly_salary + inp.taxable_additional_income - total_deductions
        )
        if epf_eligible < Decimal(0):
            epf_eligible = Decimal("0.00")
        epf_emp, epf_empr = self._calculate_epf(epf_eligible, inp.socso_category)

        # 6. SOCSO
        socso_empr, socso_emp = self._calculate_socso(
            gross_salary, inp.socso_category, inp.include_non_employment_injury
        )

        # 7. EIS
        eis_empr, eis_emp = self._calculate_eis(gross_salary)

        # 8. PCB
        pcb_amount = self._calculate_pcb(
            gross_salary,
            epf_emp,
            inp.spouse_eligible,
            inp.children_count,
            config.get("pcb", {}),
        )

        # 9. Nett Salary
        nett_salary = (
            gross_salary
            - epf_emp
            - socso_emp
            - eis_emp
            - pcb_amount
            + inp.nontaxable_additional_income
        )
        if nett_salary < Decimal(0):
            nett_salary = Decimal("0.00")

        return {
            "inputs": {
                "monthly_salary": round(float(inp.monthly_salary), 2),
                "overtime_weekday_hours": float(inp.overtime_weekday_hours),
                "overtime_weekend_hours": float(inp.overtime_weekend_hours),
                "overtime_holiday_hours": float(inp.overtime_holiday_hours),
                "late_hours": float(inp.late_hours),
                "unpaid_leave_days": float(inp.unpaid_leave_days),
                "taxable_additional_income": round(
                    float(inp.taxable_additional_income), 2
                ),
                "nontaxable_additional_income": round(
                    float(inp.nontaxable_additional_income), 2
                ),
                "socso_category": inp.socso_category,
                "spouse_eligible": inp.spouse_eligible,
                "children_count": inp.children_count,
                "marital": inp.marital_status,
                "month": inp.month,
                "year": inp.year,
            },
            "rates": {
                "hourly_rate": round(float(hourly_rate_ot), 4),
                "hourly_rate_ot": round(float(hourly_rate_ot), 4),
                "hourly_rate_late": round(float(hourly_rate_late), 4),
                "unpaid_leave_rate": round(float(unpaid_leave_rate), 4),
            },
            "additions": {
                "overtime_weekday_pay": round(float(ot_weekday_pay), 2),
                "overtime_weekend_pay": round(float(ot_weekend_pay), 2),
                "overtime_holiday_pay": round(float(ot_holiday_pay), 2),
                "total_overtime_pay": round(float(total_ot_pay), 2),
                "taxable_additional_income": round(
                    float(inp.taxable_additional_income), 2
                ),
                "nontaxable_additional_income": round(
                    float(inp.nontaxable_additional_income), 2
                ),
            },
            "deductions": {
                "late_deduction": round(float(late_deduction), 2),
                "unpaid_leave_deduction": round(float(unpaid_leave_deduction), 2),
                "total_deductions": round(float(total_deductions), 2),
            },
            "gross_salary": round(float(gross_salary), 2),
            "statutory": {
                "epf_employee": round(float(epf_emp), 2),
                "epf_employer": round(float(epf_empr), 2),
                "socso_employee": round(float(socso_emp), 2),
                "socso_employer": round(float(socso_empr), 2),
                "eis_employee": round(float(eis_emp), 2),
                "eis_employer": round(float(eis_empr), 2),
                "pcb": round(float(pcb_amount), 2),
            },
            "nett_salary": round(float(nett_salary), 2),
        }

    def _calculate_epf(
        self, epf_eligible: Decimal, category: str
    ) -> tuple[Decimal, Decimal]:
        if epf_eligible <= Decimal(0):
            return Decimal("0.00"), Decimal("0.00")

        if epf_eligible > Decimal(20000):
            if category == "first_category":
                emp = (epf_eligible * Decimal("0.11")).quantize(CENTS, ROUND_HALF_UP)
                empr = (epf_eligible * Decimal("0.12")).quantize(CENTS, ROUND_HALF_UP)
                return emp, empr
            else:
                return Decimal("0.00"), (epf_eligible * Decimal("0.04")).quantize(
                    CENTS, ROUND_HALF_UP
                )

        intervals = (
            self.repo.epf_cat_a if category == "first_category" else self.repo.epf_cat_b
        )
        for interval in intervals:
            if interval.matches(epf_eligible):
                return interval.employee_share.quantize(
                    CENTS, ROUND_HALF_UP
                ), interval.employer_share.quantize(CENTS, ROUND_HALF_UP)

        raise ValueError(f"No matching EPF tier found for RM {epf_eligible}")

    def _calculate_socso(
        self, gross: Decimal, category: str, include_non_employment_injury: bool
    ) -> tuple[Decimal, Decimal]:
        if gross <= Decimal(0):
            return Decimal("0.00"), Decimal("0.00")

        for interval in self.repo.socso_intervals:
            if interval.matches(gross):
                cat_data = interval.extra_data.get(category, {})
                empr = to_decimal(cat_data.get("employer_share", 0.0))
                invalidity = to_decimal(cat_data.get("employee_share_invalidity", 0.0))
                injury = to_decimal(
                    cat_data.get("employee_share_non_employment_injury", 0.0)
                )

                emp = invalidity + (
                    injury if include_non_employment_injury else Decimal(0)
                )
                return empr.quantize(CENTS, ROUND_HALF_UP), emp.quantize(
                    CENTS, ROUND_HALF_UP
                )

        raise ValueError(f"No matching SOCSO tier found for RM {gross}")

    def _calculate_eis(self, gross: Decimal) -> tuple[Decimal, Decimal]:
        if gross <= Decimal(0):
            return Decimal("0.00"), Decimal("0.00")

        for interval in self.repo.eis_intervals:
            if interval.matches(gross):
                return interval.employer_share.quantize(
                    CENTS, ROUND_HALF_UP
                ), interval.employee_share.quantize(CENTS, ROUND_HALF_UP)

        raise ValueError(f"No matching EIS tier found for RM {gross}")

    def _calculate_pcb(
        self,
        gross: Decimal,
        epf_emp: Decimal,
        spouse_eligible: bool,
        children_count: int,
        pcb_config: dict,
    ) -> Decimal:
        annual_income = gross * Decimal(12)
        annual_epf = epf_emp * Decimal(12)

        reliefs = pcb_config.get("reliefs", {})
        self_relief = to_decimal(reliefs.get("self", 9000.0))
        spouse_relief = (
            to_decimal(reliefs.get("spouse", 4000.0))
            if spouse_eligible
            else Decimal(0)
        )
        child_relief = to_decimal(reliefs.get("child", 2000.0))
        epf_cap = to_decimal(reliefs.get("epf", 4000.0))

        epf_relief = min(annual_epf, epf_cap)
        total_relief = (
            self_relief
            + spouse_relief
            + (child_relief * Decimal(children_count))
            + epf_relief
        )

        chargeable = annual_income - total_relief
        if chargeable <= Decimal(37333):
            return Decimal("0.00")

        for bracket in self.repo.pcb_brackets:
            lower, upper = parse_interval(bracket["Chargeable Income"])
            if chargeable > lower and (upper is None or chargeable <= upper):
                prev_tax = Decimal(str(bracket["previous tax total"]).replace(",", ""))
                rate = Decimal(str(bracket["Rate"]))
                annual_tax = prev_tax + ((chargeable - lower) * rate)
                return (annual_tax / Decimal(12)).quantize(CENTS, ROUND_HALF_UP)

        raise ValueError(
            f"No matching PCB bracket found for chargeable income RM {chargeable}"
        )
