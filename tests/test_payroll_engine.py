import os
import sys
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from core.payroll_engine import PayrollEngine, PayrollInput, parse_interval


class TestPayrollEngine(unittest.TestCase):

    def setUp(self):
        self.engine = PayrollEngine.default()

    def test_parse_interval(self):
        lower, upper = parse_interval(">30;<=50")
        self.assertEqual(lower, Decimal(30))
        self.assertEqual(upper, Decimal(50))

        lower_single, upper_single = parse_interval(">6000")
        self.assertEqual(lower_single, Decimal(6000))
        self.assertIsNone(upper_single)

    def test_part_timer_calculation(self):
        inp = PayrollInput(
            is_part_timer=True,
            total_working_hours=Decimal("40.0"),
            hourly_rate=Decimal("15.50"),
            taxable_additional_income=Decimal("50.00")
        )
        res = self.engine.calculate(inp)
        self.assertTrue(res["is_part_timer"])
        self.assertEqual(res["nett_salary"], 670.0)
        self.assertEqual(res["gross_salary"], 670.0)

    def test_full_timer_basic_payroll(self):
        inp = PayrollInput(
            monthly_salary=Decimal("5000.00"),
            socso_category="first_category",
            spouse_eligible=False,
            children_count=0,
            month=7,
            year=2026
        )
        res = self.engine.calculate(inp)
        self.assertFalse(res.get("is_part_timer", False))
        self.assertEqual(res["gross_salary"], 5000.0)
        self.assertGreater(res["statutory"]["epf_employee"], 0)
        self.assertGreater(res["statutory"]["epf_employer"], 0)
        self.assertGreater(res["statutory"]["socso_employee"], 0)
        self.assertGreater(res["statutory"]["socso_employer"], 0)
        self.assertGreater(res["statutory"]["eis_employee"], 0)
        self.assertGreater(res["statutory"]["eis_employer"], 0)

    def test_epf_high_earner_cap(self):
        # Salary > RM 20,000 should trigger percentage-based rates (11% / 12%)
        inp = PayrollInput(monthly_salary=Decimal("25000.00"), socso_category="first_category")
        res = self.engine.calculate(inp)
        self.assertEqual(res["statutory"]["epf_employee"], 2750.0) # 11% of 25,000
        self.assertEqual(res["statutory"]["epf_employer"], 3000.0) # 12% of 25,000

    def test_socso_injury_option(self):
        inp_base = PayrollInput(monthly_salary=Decimal("3000.00"), include_non_employment_injury=False)
        res_base = self.engine.calculate(inp_base)

        inp_injury = PayrollInput(monthly_salary=Decimal("3000.00"), include_non_employment_injury=True)
        res_injury = self.engine.calculate(inp_injury)

        self.assertGreaterEqual(res_injury["statutory"]["socso_employee"], res_base["statutory"]["socso_employee"])

    def test_pcb_tax_reliefs(self):
        # Higher reliefs should reduce PCB tax
        inp_single = PayrollInput(monthly_salary=Decimal("8000.00"), spouse_eligible=False, children_count=0)
        res_single = self.engine.calculate(inp_single)

        inp_family = PayrollInput(monthly_salary=Decimal("8000.00"), spouse_eligible=True, children_count=3)
        res_family = self.engine.calculate(inp_family)

        self.assertLess(res_family["statutory"]["pcb"], res_single["statutory"]["pcb"])

    def test_zero_salary(self):
        inp = PayrollInput(monthly_salary=Decimal("0.00"))
        res = self.engine.calculate(inp)
        self.assertEqual(res["gross_salary"], 0.0)
        self.assertEqual(res["nett_salary"], 0.0)
        self.assertEqual(res["statutory"]["epf_employee"], 0.0)
        self.assertEqual(res["statutory"]["socso_employee"], 0.0)

    def test_payroll_input_from_dict(self):
        inp = PayrollInput.from_dict({
            "monthly_salary": 4500.0,
            "socso_category": "first_category",
            "spouse_eligible": True,
            "children_count": 2
        })
        res = self.engine.calculate(inp)
        self.assertEqual(res["gross_salary"], 4500.0)
        self.assertIn("nett_salary", res)
        self.assertIn("statutory", res)

if __name__ == "__main__":
    unittest.main()
