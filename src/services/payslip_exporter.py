import calendar


class PayslipExporter:
    """
    Dedicated service for generating HTML payslip documents and exporting them to PDF.
    Separates document layout, CSS styling, and page geometry from UI event handlers.
    """

    @staticmethod
    def render_html(res: dict, company_name: str = "DEMO MALAYSIA ENTERPRISE") -> str:
        """
        Generates a standalone HTML payslip document string from a calculation result dict.
        Pure function - no GUI or file I/O dependencies.
        """
        inputs = res.get("inputs", {})
        additions = res.get("additions", {})
        deductions = res.get("deductions", {})
        stat = res.get("statutory", {})
        rates = res.get("rates", {})

        month_name = calendar.month_name[inputs.get("month", 7)]
        year_val = inputs.get("year", 2026)

        if res.get("is_part_timer"):
            shifts = inputs.get("part_time_shifts", [])
            shift_rows_html = ""
            for idx, s in enumerate(shifts, start=1):
                shift_rows_html += f"""
                <tr>
                    <td>Entry {idx}</td>
                    <td class="right">{s.get('days', 0.0):.1f} days</td>
                    <td class="right">{s.get('hours', 0.0):.2f} hrs</td>
                    <td class="right">{s.get('subtotal_hours', 0.0):.2f} hrs</td>
                </tr>
                """

            hourly_rate_display = f"RM {rates.get('hourly_rate', inputs.get('hourly_rate', 0.0)):,.2f}"
            total_hours = inputs.get("total_working_hours", 0.0)
            base_wages = additions.get("base_wages", total_hours * inputs.get("hourly_rate", 0.0))
            add_income = additions.get("taxable_additional_income", inputs.get("taxable_additional_income", 0.0))

            return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            color: #334155;
            line-height: 1.5;
            margin: 40px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .company-name {{
            font-size: 26px;
            font-weight: bold;
            color: #1E3A8A;
            margin: 0;
        }}
        .payslip-title {{
            font-size: 16px;
            font-weight: 600;
            color: #64748B;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .meta-table, .breakdown-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 25px;
        }}
        .meta-table td {{
            padding: 6px 12px;
            border: none;
        }}
        .breakdown-table th {{
            background-color: #F8FAFC;
            color: #475569;
            font-weight: bold;
            text-align: left;
            border-bottom: 2px solid #E2E8F0;
            padding: 10px 12px;
        }}
        .breakdown-table td {{
            padding: 10px 12px;
            border-bottom: 1px solid #F1F5F9;
        }}
        .breakdown-table tr.total {{
            background-color: #F1F5F9;
            font-weight: bold;
            color: #0F172A;
        }}
        .breakdown-table tr.nett-total {{
            background-color: #ECFDF5;
            font-weight: 800;
            font-size: 16px;
            color: #065F46;
            border-top: 2px solid #10B981;
            border-bottom: 2px solid #10B981;
        }}
        .right {{
            text-align: right;
        }}
        .text-bold {{
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="header">
        <p class="company-name">{company_name}</p>
        <span class="payslip-title">Part-Time Official Pay Slip</span>
    </div>
    
    <table class="meta-table">
        <tr>
            <td class="text-bold">Employment Type:</td>
            <td>Part-Timer (Hourly)</td>
            <td class="text-bold">Hourly Rate:</td>
            <td>{hourly_rate_display} / hr</td>
        </tr>
        <tr>
            <td class="text-bold">Pay Period:</td>
            <td>{month_name} {year_val}</td>
            <td class="text-bold">Statutory Deductions:</td>
            <td>Exempt (No EPF/SOCSO/EIS/PCB)</td>
        </tr>
    </table>

    <table class="breakdown-table">
        <thead>
            <tr>
                <th>Working Hours (Day × Hour)</th>
                <th class="right">Days Count</th>
                <th class="right">Hours / Day</th>
                <th class="right">Subtotal Hours</th>
            </tr>
        </thead>
        <tbody>
            {shift_rows_html}
            <tr class="total">
                <td colspan="3">TOTAL WORKING HOURS</td>
                <td class="right">{total_hours:,.2f} hrs</td>
            </tr>
        </tbody>
    </table>
    
    <table class="breakdown-table">
        <thead>
            <tr>
                <th>Earnings Breakdown</th>
                <th class="right">Rate</th>
                <th class="right">Amount (RM)</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Base Wages ({total_hours:,.2f} hrs)</td>
                <td class="right">{hourly_rate_display}</td>
                <td class="right">{base_wages:,.2f}</td>
            </tr>
            <tr>
                <td>Additional Income (Allowances / Bonuses)</td>
                <td class="right">-</td>
                <td class="right" style="color: #10B981;">+{add_income:,.2f}</td>
            </tr>
            <tr class="total">
                <td colspan="2">GROSS SALARY</td>
                <td class="right">{res.get('gross_salary', 0.0):,.2f}</td>
            </tr>
            <tr class="nett-total">
                <td colspan="2">NETT TAKE-HOME SALARY</td>
                <td class="right">RM {res.get('nett_salary', 0.0):,.2f}</td>
            </tr>
        </tbody>
    </table>
    
    <div style="margin-top: 40px; font-size: 13px; text-align: center; color: #94A3B8;">
        This is a computer-generated document. No signature is required.
    </div>
</body>
</html>
"""

        socso_cat_display = str(inputs.get("socso_category", "")).replace("_", " ").title()
        marital_display = str(inputs.get("marital", ""))
        spouse_display = "Claimed" if inputs.get("spouse_eligible") else "None"

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            color: #334155;
            line-height: 1.5;
            margin: 40px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .company-name {{
            font-size: 26px;
            font-weight: bold;
            color: #1E3A8A;
            margin: 0;
        }}
        .payslip-title {{
            font-size: 16px;
            font-weight: 600;
            color: #64748B;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .meta-table, .breakdown-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 25px;
        }}
        .meta-table td {{
            padding: 6px 12px;
            border: none;
        }}
        .breakdown-table th {{
            background-color: #F8FAFC;
            color: #475569;
            font-weight: bold;
            text-align: left;
            border-bottom: 2px solid #E2E8F0;
            padding: 10px 12px;
        }}
        .breakdown-table td {{
            padding: 10px 12px;
            border-bottom: 1px solid #F1F5F9;
        }}
        .breakdown-table tr.total {{
            background-color: #F1F5F9;
            font-weight: bold;
            color: #0F172A;
        }}
        .breakdown-table tr.nett-total {{
            background-color: #ECFDF5;
            font-weight: 800;
            font-size: 16px;
            color: #065F46;
            border-top: 2px solid #10B981;
            border-bottom: 2px solid #10B981;
        }}
        .right {{
            text-align: right;
        }}
        .text-bold {{
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="header">
        <p class="company-name">{company_name}</p>
        <span class="payslip-title">Official Pay Slip</span>
    </div>
    
    <table class="meta-table">
        <tr>
            <td class="text-bold">Employee Status:</td>
            <td>{socso_cat_display}</td>
            <td class="text-bold">Marital Status:</td>
            <td>{marital_display}</td>
        </tr>
        <tr>
            <td class="text-bold">Spouse Relief:</td>
            <td>{spouse_display}</td>
            <td class="text-bold">Children Count:</td>
            <td>{inputs.get('children_count', 0)}</td>
        </tr>
        <tr>
            <td class="text-bold">Pay Period:</td>
            <td>{month_name} {year_val}</td>
            <td class="text-bold"></td>
            <td></td>
        </tr>
    </table>
    
    <table class="breakdown-table">
        <thead>
            <tr>
                <th>Earnings Breakdown</th>
                <th class="right">Employee Share (RM)</th>
                <th class="right">Employer Share (RM)</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Base Salary</td>
                <td class="right">{inputs.get('monthly_salary', 0.0):,.2f}</td>
                <td class="right">-</td>
            </tr>
            <tr>
                <td>Weekday Overtime ({inputs.get('overtime_weekday_hours', 0.0)} hrs)</td>
                <td class="right">{additions.get('overtime_weekday_pay', 0.0):,.2f}</td>
                <td class="right">-</td>
            </tr>
            <tr>
                <td>Weekend Overtime ({inputs.get('overtime_weekend_hours', 0.0)} hrs)</td>
                <td class="right">{additions.get('overtime_weekend_pay', 0.0):,.2f}</td>
                <td class="right">-</td>
            </tr>
            <tr>
                <td>Public Holiday Overtime ({inputs.get('overtime_holiday_hours', 0.0)} hrs)</td>
                <td class="right">{additions.get('overtime_holiday_pay', 0.0):,.2f}</td>
                <td class="right">-</td>
            </tr>
            <tr>
                <td>Taxable Additional Income</td>
                <td class="right">{additions.get('taxable_additional_income', 0.0):,.2f}</td>
                <td class="right">-</td>
            </tr>
            
            <thead>
                <tr>
                    <th>Deductions & Statutory Contributions</th>
                    <th class="right"></th>
                    <th class="right"></th>
                </tr>
            </thead>
            <tr>
                <td>Late Hours Deduction ({inputs.get('late_hours', 0.0)} hrs)</td>
                <td class="right" style="color: #EF4444;">-{deductions.get('late_deduction', 0.0):,.2f}</td>
                <td class="right">-</td>
            </tr>
            <tr>
                <td>Unpaid Leave Deduction ({inputs.get('unpaid_leave_days', 0.0)} days)</td>
                <td class="right" style="color: #EF4444;">-{deductions.get('unpaid_leave_deduction', 0.0):,.2f}</td>
                <td class="right">-</td>
            </tr>
            
            <tr class="total">
                <td>GROSS SALARY</td>
                <td class="right">{res.get('gross_salary', 0.0):,.2f}</td>
                <td class="right">-</td>
            </tr>
            
            <tr>
                <td>EPF Contribution</td>
                <td class="right" style="color: #EF4444;">-{stat.get('epf_employee', 0.0):,.2f}</td>
                <td class="right">{stat.get('epf_employer', 0.0):,.2f}</td>
            </tr>
            <tr>
                <td>SOCSO Contribution</td>
                <td class="right" style="color: #EF4444;">-{stat.get('socso_employee', 0.0):,.2f}</td>
                <td class="right">{stat.get('socso_employer', 0.0):,.2f}</td>
            </tr>
            <tr>
                <td>EIS Contribution</td>
                <td class="right" style="color: #EF4444;">-{stat.get('eis_employee', 0.0):,.2f}</td>
                <td class="right">{stat.get('eis_employer', 0.0):,.2f}</td>
            </tr>
            <tr>
                <td>PCB Monthly Tax Deduction</td>
                <td class="right" style="color: #EF4444;">-{stat.get('pcb', 0.0):,.2f}</td>
                <td class="right">-</td>
            </tr>
            
            <tr>
                <td>Non-Taxable Additional Income</td>
                <td class="right" style="color: #10B981;">+{additions.get('nontaxable_additional_income', 0.0):,.2f}</td>
                <td class="right">-</td>
            </tr>
            
            <tr class="nett-total">
                <td>NETT TAKE-HOME SALARY</td>
                <td class="right">RM {res.get('nett_salary', 0.0):,.2f}</td>
                <td class="right"></td>
            </tr>
        </tbody>
    </table>
    
    <div style="margin-top: 40px; font-size: 13px; text-align: center; color: #94A3B8;">
        This is a computer-generated document. No signature is required.
    </div>
</body>
</html>
"""

    @classmethod
    def export_pdf(cls, res: dict, file_path: str, company_name: str = "DEMO MALAYSIA ENTERPRISE") -> bool:
        """
        Renders HTML and prints to PDF file using PySide6.
        """
        from PySide6.QtGui import QPageSize, QPdfWriter, QTextDocument

        html_content = cls.render_html(res, company_name=company_name)
        doc = QTextDocument()
        doc.setHtml(html_content)

        writer = QPdfWriter(file_path)
        writer.setResolution(96)
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        doc.print_(writer)
        return True
