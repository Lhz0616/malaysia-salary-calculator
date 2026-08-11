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

if __name__ == "__main__":
    unittest.main()
