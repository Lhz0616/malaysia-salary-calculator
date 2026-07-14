# 💰 Salary + Statutory + PCB Calculator (Malaysia)

---

## 🎯 Objective

A **desktop application** (Python + PySide6) that calculates, for a Malaysian employee:

* Gross Salary
* Overtime Pay (Weekday / Weekend / Public Holiday)
* Deductions (Late Hours, Unpaid Leave)
* EPF (Employee + Employer)
* SOCSO (Employee + Employer)
* EIS (Employee + Employer)
* PCB (Monthly Tax Deduction)
* Final Nett Salary

The system is **modular, data-driven, and configurable**. Statutory rates live in JSON tables under `src/data/`, not in code.

---

## ⚙️ Tech Stack

* Language: **Python 3.12+**
* Environment Manager: **`uv`** (mandatory)
* Packaging: **PyInstaller** (`--onefile`)
* UI Framework: **PySide6** (the only framework currently implemented)

---

## 📁 Project Structure

```
salary_calculator/
├── src/
│   ├── main.py                      # QApplication bootstrap -> MainWindow
│   ├── core/
│   │   ├── salary_calculator.py     # calculate_salary_package() master pipeline
│   │   ├── config_loader.py         # get_resource_path(), load/save config, parse_contribution_range()
│   │   ├── epf_calculator.py        # calculate_epf()  (table-driven)
│   │   ├── socso_calculator.py      # calculate_socso()
│   │   ├── eis_calculator.py        # calculate_eis()
│   │   ├── pcb_calculator.py        # calculate_pcb() + parse_pcb_bracket()
│   │   └── helper.py                # to_decimal(), CENTS quantization
│   ├── ui/
│   │   └── main_window.py           # MainWindow + ConfigEditorDialog
│   └── data/
│       ├── config.json              # global config (days, OT rates, PCB reliefs)
│       ├── epf_contribution_rates.json
│       ├── socso_contribution.json
│       ├── eis_contribution.json
│       └── income_tax_bracket_2025.json
├── prompt.md
├── pyproject.toml
└── uv.lock
```

---

## 🔢 Money & Precision (applies everywhere)

* All monetary values are handled as `decimal.Decimal`, never raw `float`.
* `helper.to_decimal(value)` builds a `Decimal` **from the string form** of a value to avoid binary float error.
* Final amounts are quantized to 2 decimal places with `ROUND_HALF_UP`.
* The JSON contribution tables use `Decimal`-parsed range strings (`">10.01;<=20.00"`); the EIS table stores its amounts as strings (`"0.05"`) and is cast on load.

---

## 🛠️ Global Configuration — `src/data/config.json`

```json
{
  "fixed_overtime_days": 26,
  "fixed_unpaid_leave_days": "calendar_days",
  "fixed_late_hours_days": "calendar_days",
  "overtime_rates": {
    "weekday": 1.5,
    "weekend": 2.0,
    "public_holiday": 3.0
  },
  "pcb": {
    "tax_brackets_file": "src/data/income_tax_bracket_2025.json",
    "reliefs": {
      "self": 9000,
      "spouse": 4000,
      "child": 2000,
      "epf": 4000
    }
  }
}
```

Field rules:

| Key | Meaning |
|---|---|
| `fixed_overtime_days` | Base day count (default **26**) used for the **overtime** hourly rate `= monthly_salary / (days * 8)`. |
| `fixed_unpaid_leave_days` | Base day count for the unpaid-leave daily rate. May be `"calendar_days"` (resolved to the actual number of days in the chosen month via `calendar.monthrange`) or a float. |
| `fixed_late_hours_days` | Base day count for the late-deduction hourly rate. Same `"calendar_days"` / float semantics. |
| `overtime_rates` | Per-type multipliers (weekday / weekend / public_holiday). |
| `pcb.tax_brackets_file` | Path (relative to project root) to the progressive tax table. |
| `pcb.reliefs` | Tax relief amounts: `self`, `spouse`, `child` (per child), and `epf` (cap on EPF relief). |

> **EPF is not configurable via `config.json`.** The Config Editor has **no** EPF tab by design — EPF rates are statutory and edited directly in `epf_contribution_rates.json` (see below). The engine never reads an `epf` config block.

---

## 🧮 Salary Calculation Flow (MASTER PIPELINE)

Implemented in `core/salary_calculator.calculate_salary_package(...)`.

### Step 0: Employment mode

* **Full-timer** (default): full pipeline with statutory deductions.
* **Part-timer** (`is_part_timer=True`): shortcut — no statutory deductions:

  ```
  nett = total_working_hours * hourly_rate + taxable_additional_income
  gross_salary = nett   # no statutory, no overtime breakdown
  ```

### Step 1: Base Salary Adjustments (full-timer inputs)

* Monthly (base) Salary
* Overtime — **three separate hour inputs**: Weekday, Weekend, Public Holiday
* Late Hours
* Unpaid Leave (entered in hours)
* Taxable Additional Income (subject to EPF/SOCSO/EIS & PCB)
* Non-Taxable Additional Income (added to nett only — see Step 9)

### Step 2: Hourly rates

```text
hourly_rate_ot   = monthly_salary / (fixed_overtime_days * 8)
hourly_rate_late = monthly_salary / (late_days_base * 8)          # uses to_decimal()
unpaid_rate      = monthly_salary / (unpaid_days_base or *8)      # uses to_decimal()
```

`late_days_base` and `unpaid_days_base` come from `fixed_late_hours_days` / `fixed_unpaid_leave_days`; `"calendar_days"` is resolved to the actual days of the selected month. Unpaid leave entered as a multiple of 8 hours is treated as whole days.

### Step 3: Overtime Pay (split by type)

```text
overtime_weekday_pay = weekday_hours    * hourly_rate_ot * overtime_rates.weekday      # 1.5
overtime_weekend_pay = weekend_hours    * hourly_rate_ot * overtime_rates.weekend      # 2.0
overtime_holiday_pay = holiday_hours    * hourly_rate_ot * overtime_rates.public_holiday # 3.0
total_overtime_pay   = weekday + weekend + holiday
```

### Step 4: Deductions (Decimal, HALF_UP)

```text
late_deduction         = hourly_rate_late * late_hours
unpaid_leave_deduction = unpaid_rate      * unpaid_leave_hours
total_deductions       = late_deduction + unpaid_leave_deduction
```

### Step 5: Gross Salary

```text
gross_salary = monthly_salary + total_overtime_pay + taxable_additional_income - total_deductions
if gross_salary < 0: gross_salary = 0
```

### Step 6: EPF Calculation (table-driven)

Base used for EPF is **not** gross — it is:

```text
epf_eligible_salary = monthly_salary + taxable_additional_income - total_deductions
if epf_eligible_salary < 0: epf_eligible_salary = 0
```

`calculate_epf(epf_eligible_salary, category)` reads `src/data/epf_contribution_rates.json` (KWSP Third Schedule, effective **1 Oct 2025**):

* Two categories: `categoryA` = `first_category` (employee < 60), `categoryB` = `second_category` (employee ≥ 60).
* For a matched wage tier it returns the **fixed** `employer_contribution` and `employee_contribution` amounts from the table (these are absolute RM amounts per the schedule, not a flat percentage).
* Out-of-range helpers:
  * `salary > 20000` → first: employee `0.11`, employer `0.12`; second: employee `0.00`, employer `0.04`.
  * `salary <= 0` → `(0.00, 0.00)`.
* Raises `ValueError` if no tier matches.

> ⚠️ EPF is **data-driven** — do not hardcode rates; the table in `epf_contribution_rates.json` is the source of truth. The `config["epf"]` percentage block is ignored by this function.

### Step 7: SOCSO Calculation

`calculate_socso(gross_salary, category, include_non_employment_injury)` reads `src/data/socso_contribution.json`:

* Each tier has `monthly_salary` range plus `first_category` / `second_category` blocks.
* `second_category` = employee **≥ 60 years old**.
* Employee share = `employee_share_invalidity` **+** `employee_share_non_employment_injury` **only when** `include_non_employment_injury=True` (otherwise invalidity portion only).
* Employer share = `employer_share`.
* ⚠️ Do **not** hardcode SOCSO values — load and match the range from the JSON table.

### Step 8: EIS Calculation

`calculate_eis(gross_salary)` reads `src/data/eis_contribution.json`:

* Matches the `amount_of_wages` range; employer and employee contributions are **equal** (`employer_contribution == employee_contribution`).
* Base = `gross_salary`.
* ⚠️ Data-driven — do not hardcode.

### Step 9: PCB Calculation (progressive, integrated)

`calculate_pcb(gross_salary, epf_employee, spouse_eligible, children_count, pcb_config)`:

```text
annual_income = gross_salary * 12
annual_epf    = epf_employee * 12

self_relief   = reliefs.self                         # 9000
spouse_relief = reliefs.spouse if spouse_eligible else 0   # 4000
child_relief  = reliefs.child * children_count       # 2000 / child
epf_relief    = min(annual_epf, reliefs.epf)         # capped at 4000

total_relief     = self_relief + spouse_relief + child_relief + epf_relief
chargeable_income = annual_income - total_relief

if chargeable_income <= 37333:        # 2026 zero-PCB threshold (RM37,333/yr)
    pcb = 0
else:
    # progressive bracket lookup from pcb_config.tax_brackets_file
    pcb = annual_tax / 12
```

* Bracket table: `src/data/income_tax_bracket_2025.json`, schema `["Chargeable Income", "Rate", "previous tax total", "current tax max"]`.
* `Chargeable Income` is parsed with `parse_pcb_bracket()` as `">=lower;<=upper"` (top bracket may be open-ended, e.g. `">1000000"`).
* For the matched bracket: `annual_tax = previous_tax_total + (chargeable_income - lower) * Rate`.
* `previous tax total` may contain commas (e.g. `"1,500"`) — strip before casting.
* `pcb` is quantized HALF_UP to 2 dp. Raises `ValueError` if no bracket matches.

> 🔥 PCB uses **gross** salary (annualized) as its starting point, then subtracts EPF relief (capped) and the other reliefs. It respects each bracket's own rate and baseline — **no flat percentage**.

### Step 10: Nett Salary (FINAL OUTPUT)

```text
nett_salary = gross_salary
            - epf_employee
            - socso_employee
            - eis_employee
            - pcb
            + nontaxable_additional_income     # added back, not taxed/contributed
if nett_salary < 0: nett_salary = 0
```

---

## 🖥️ UI Requirements (`src/ui/main_window.py`)

### Input Fields (Full-timer)

* **Period** — Month / Year (used to resolve `calendar_days`)
* **Base Monthly Salary (RM)**
* **Overtime Weekday (Hours)** — ×1.5
* **Overtime Weekend (Hours)** — ×2.0
* **Overtime Public Holiday (Hours)** — ×3.0
* **Late Deduction (Hours)**
* **Unpaid Leave (Hours)**
* **Taxable Additional Income (RM)**
* **Non-Taxable Additional Income (RM)**
* **Marital Status** — Single / Married
* **Spouse Eligible** — checkbox (enables spouse relief)
* **Number of Children**
* **SOCSO Category** — First (employee < 60) / Second (employee ≥ 60)
* **Include Non-Employment Injury Scheme** — checkbox (SOCSO employee share)

### Input Fields (Part-timer mode)

* Total Working Hours
* Hourly Rate (RM)
* Additional Income (RM)

### Output Display

* **NETT MONTHLY SALARY** (highlighted card)
* Payroll Breakdown table:
  * Gross Salary
  * Late Deduction (−)
  * Unpaid Leave Deduction (−)
  * EPF (Employee / Employer)
  * SOCSO (Employee / Employer)
  * EIS (Employee / Employer)
  * PCB Monthly Tax Deduction (−)
  * Nett Take-Home Salary
* **Export PDF Pay Slip** — renders an HTML payslip and prints to PDF (full-timer only).
* **View Configs** — opens `ConfigEditorDialog` to edit `config.json` (days, OT rates, PCB reliefs, legacy EPF rates) and live-recomputes.

Calculation runs automatically on any input change (auto-calculate).

---

## ❗ STRICT RULES

1. NO hardcoded SOCSO / EIS / EPF values — load and match from `src/data/*.json`.
2. NO flat PCB percentage — use the progressive `income_tax_bracket_2025.json` with `Chargeable Income` / `Rate` / `previous tax total` / `current tax max`.
3. All money must flow through `Decimal` + `to_decimal()`; final outputs quantized HALF_UP.
4. EPF base = `monthly_salary + taxable_additional_income − total_deductions` (not gross, not including overtime).
5. SOCSO & EIS base = `gross_salary`.
6. Nett = gross − (EPF + SOCSO + EIS + PCB employee shares) + non-taxable additional income.
7. Logic must stay modular (one calculator module per statutory component) and data-driven (new brackets/rates edited in JSON only).

---

## 🧪 Testing Requirements (suggested)

* Low salary (no PCB).
* Salary > RM5,000 (EPF table tier switch).
* With overtime (all three types) + deductions.
* With spouse + children (PCB relief reduction).
* Edge salary brackets (SOCSO/EIS range boundaries).
* Chargeable income exactly on a bracket boundary (`== upper` of one / `== lower` of next) — must not double-count or skip.
* Chargeable income below the RM37,333/yr PCB threshold → PCB = 0.
* Part-timer mode → nett = hours × rate + additional, no statutory.
* Config `calendar_days` resolution matches the selected month's real day count.

---

## 🚀 Packaging

```bash
pyinstaller --onefile src/main.py
```

`get_resource_path()` resolves data files both in dev (project root) and inside the PyInstaller bundle (`sys._MEIPASS`), with a `src/`-stripping fallback.

---

## 💡 Final Design Principle

This app behaves like a **real payroll mini-engine**, not a simple calculator:

* **Data-driven** — statutory tables live in JSON, independently versioned (e.g. when LHDN revises a schedule).
* **Modular** — `salary_calculator` orchestrates one module per component.
* **Extensible** — new brackets/rates are added/edited in the JSON files without touching code.
* **Accurate** — `Decimal` math, HALF_UP rounding, and faithful progressive-tax logic.
