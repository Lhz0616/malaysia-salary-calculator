import os
import sys
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from core.payroll_engine import PayrollEngine, PayrollInput
from services.payslip_exporter import PayslipExporter


class TestPayslipExporter(unittest.TestCase):

    def setUp(self):
        self.engine = PayrollEngine.default()
        inp = PayrollInput(
            monthly_salary=Decimal("5000.00"),
            overtime_weekday_hours=Decimal("5.0"),
            socso_category="first_category",
            month=7,
            year=2026
        )
        self.payroll_result = self.engine.calculate(inp)

    def test_render_html_structure(self):
        html = PayslipExporter.render_html(self.payroll_result, company_name="ACME CORP")
        self.assertIn("ACME CORP", html)
        self.assertIn("Official Pay Slip", html)
        self.assertIn("Base Salary", html)
        self.assertIn("5,000.00", html)
        self.assertIn("GROSS SALARY", html)
        self.assertIn("NETT TAKE-HOME SALARY", html)
        self.assertIn("EPF Contribution", html)
        self.assertIn("SOCSO Contribution", html)
        self.assertIn("EIS Contribution", html)

    def test_render_part_timer_html_structure(self):
        inp = PayrollInput(
            is_part_timer=True,
            part_time_shifts=(
                (Decimal("8.0"), Decimal("5.0")),
                (Decimal("4.0"), Decimal("3.0")),
            ),
            hourly_rate=Decimal("15.00"),
            taxable_additional_income=Decimal("50.00"),
            month=8,
            year=2026,
        )
        res = self.engine.calculate(inp)
        html = PayslipExporter.render_html(res, company_name="MALAYSIA RETAIL SDN BHD")
        self.assertIn("MALAYSIA RETAIL SDN BHD", html)
        self.assertIn("Part-Time Official Pay Slip", html)
        self.assertIn("Part-Timer (Hourly)", html)
        self.assertIn("RM 15.00 / hr", html)
        self.assertIn("Working Hours (Day × Hour)", html)
        self.assertIn("Entry 1", html)
        self.assertIn("8.00 hrs", html)
        self.assertIn("5.0 days", html)
        self.assertIn("40.00 hrs", html)
        self.assertIn("Entry 2", html)
        self.assertIn("4.00 hrs", html)
        self.assertIn("3.0 days", html)
        self.assertIn("12.00 hrs", html)
        self.assertIn("TOTAL WORKING HOURS", html)
        self.assertIn("52.00 hrs", html)
        self.assertIn("Base Wages", html)
        self.assertIn("780.00", html)
        self.assertIn("Additional Income", html)
        self.assertIn("50.00", html)
        self.assertIn("830.00", html)

if __name__ == "__main__":
    unittest.main()
