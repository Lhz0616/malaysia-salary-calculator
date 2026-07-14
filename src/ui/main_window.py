import calendar
import datetime
from decimal import Decimal
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QCheckBox, QSpinBox, QDoubleSpinBox, QRadioButton,
    QButtonGroup, QPushButton, QGroupBox, QFileDialog, QMessageBox,
    QDialog, QScrollArea, QFrame, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator, QIntValidator, QTextDocument, QPdfWriter, QPageSize, QColor, QFont

from core.salary_calculator import calculate_salary_package
from core.config_loader import get_configs, save_all_config

# Rows shown in the payroll breakdown table for each employment mode.
# Each entry is (label, merged?) where merged rows span the Employee + Employer columns.
FULLTIMER_BREAKDOWN_ROWS = [
    ("Gross Salary", True),
    ("Late Deduction", True),
    ("Unpaid Leave Deduction", True),
    ("EPF (Statutory)", False),
    ("SOCSO (Statutory)", False),
    ("EIS (Statutory)", False),
    ("PCB Monthly Tax Deduction", True),
    ("Nett Take-Home Salary", True),
]

PARTTIMER_BREAKDOWN_ROWS = [
    ("Nett Take-Home Salary", True),
]

class ConfigEditorDialog(QDialog):
    """
    A pop-up dialog that allows editing global config JSON data.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuration Editor")
        self.resize(550, 480)
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
            }
            QLabel {
                color: #F8FAFC;
                font-weight: 500;
                font-size: 14px;
                font-family: 'Arial';
            }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #1E293B;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 5px 10px;
                color: #F8FAFC;
                font-size: 14px;
                font-family: 'Arial';
            }
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
                border: 1px solid #3B82F6;
                background-color: #1E293B;
            }
            QTabWidget::pane {
                border: 1px solid #334155;
                background-color: #0F172A;
                border-radius: 6px;
                padding: 8px;
            }
            QTabBar::tab {
                background-color: #1E293B;
                color: #94A3B8;
                border: 1px solid #334155;
                padding: 6px 10px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: bold;
                font-size: 14px;
                font-family: 'Arial';
            }
            QTabBar::tab:selected {
                background-color: #3B82F6;
                color: #FFFFFF;
                border-color: #3B82F6;
            }
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 14px;
                font-family: 'Arial';
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
            QPushButton#cancelBtn {
                background-color: transparent;
                border: 1px solid #475569;
                color: #94A3B8;
                font-family: 'Arial';
            }
            QPushButton#cancelBtn:hover {
                background-color: #1E293B;
                color: #F8FAFC;
            }
        """)
        
        # Load active configs (global in-memory collection; config page edits "config")
        try:
            self.configs = get_configs()
            self.config = self.configs.get("config", {})
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load configuration: {e}")
            self.configs = {}
            self.config = {}
            
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        title_lbl = QLabel("Modify Global System Configuration", self)
        title_lbl.setStyleSheet("font-size: 17px; font-weight: bold; color: #38BDF8; font-family: 'Segoe UI';")
        layout.addWidget(title_lbl)
        
        # Tab Widget
        self.tabs = QTabWidget(self)
        
        # TAB 1: Workdays & Overtime Rates
        tab1 = QWidget()
        form1 = QFormLayout(tab1)
        form1.setSpacing(10)
        
        self.spin_ot_days = QSpinBox(self)
        self.spin_ot_days.setRange(1, 31)
        self.spin_ot_days.setValue(int(self.config.get("fixed_overtime_days", 26)))
        form1.addRow("Fixed Overtime Days/Month:", self.spin_ot_days)
        
        self.txt_unpaid_days_cfg = QLineEdit(self)
        self.txt_unpaid_days_cfg.setText(str(self.config.get("fixed_unpaid_leave_days", "calendar_days")))
        form1.addRow("Unpaid Leave Base Days (e.g. 'calendar_days' or float):", self.txt_unpaid_days_cfg)
        
        self.txt_late_days_cfg = QLineEdit(self)
        self.txt_late_days_cfg.setText(str(self.config.get("fixed_late_hours_days", "calendar_days")))
        form1.addRow("Late Hours Base Days (e.g. 'calendar_days' or float):", self.txt_late_days_cfg)
        
        ot_rates = self.config.get("overtime_rates", {})
        self.spin_rate_weekday = QDoubleSpinBox(self)
        self.spin_rate_weekday.setRange(0.0, 10.0)
        self.spin_rate_weekday.setSingleStep(0.1)
        self.spin_rate_weekday.setValue(float(ot_rates.get("weekday", 1.5)))
        form1.addRow("Weekday OT multiplier:", self.spin_rate_weekday)
        
        self.spin_rate_weekend = QDoubleSpinBox(self)
        self.spin_rate_weekend.setRange(0.0, 10.0)
        self.spin_rate_weekend.setSingleStep(0.1)
        self.spin_rate_weekend.setValue(float(ot_rates.get("weekend", 2.0)))
        form1.addRow("Weekend OT multiplier:", self.spin_rate_weekend)
        
        self.spin_rate_holiday = QDoubleSpinBox(self)
        self.spin_rate_holiday.setRange(0.0, 10.0)
        self.spin_rate_holiday.setSingleStep(0.1)
        self.spin_rate_holiday.setValue(float(ot_rates.get("public_holiday", 3.0)))
        form1.addRow("Public Holiday OT multiplier:", self.spin_rate_holiday)
        
        self.tabs.addTab(tab1, "Wages & OT")
        
        # TAB 2: PCB Tax Reliefs
        tab3 = QWidget()
        form3 = QFormLayout(tab3)
        form3.setSpacing(10)
        
        pcb_cfg = self.config.get("pcb", {})
        reliefs = pcb_cfg.get("reliefs", {})
        
        self.spin_relief_self = QSpinBox(self)
        self.spin_relief_self.setRange(0, 50000)
        self.spin_relief_self.setSingleStep(500)
        self.spin_relief_self.setValue(int(reliefs.get("self", 9000)))
        form3.addRow("Self Tax Relief (RM):", self.spin_relief_self)
        
        self.spin_relief_spouse = QSpinBox(self)
        self.spin_relief_spouse.setRange(0, 50000)
        self.spin_relief_spouse.setSingleStep(500)
        self.spin_relief_spouse.setValue(int(reliefs.get("spouse", 4000)))
        form3.addRow("Spouse Tax Relief (RM):", self.spin_relief_spouse)
        
        self.spin_relief_child = QSpinBox(self)
        self.spin_relief_child.setRange(0, 50000)
        self.spin_relief_child.setSingleStep(500)
        self.spin_relief_child.setValue(int(reliefs.get("child", 2000)))
        form3.addRow("Child Tax Relief (RM/child):", self.spin_relief_child)
        
        self.spin_relief_epf = QSpinBox(self)
        self.spin_relief_epf.setRange(0, 50000)
        self.spin_relief_epf.setSingleStep(500)
        self.spin_relief_epf.setValue(int(reliefs.get("epf", 4000)))
        form3.addRow("EPF Contribution Max Relief (RM):", self.spin_relief_epf)
        
        self.tabs.addTab(tab3, "PCB Reliefs")
        
        layout.addWidget(self.tabs)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel", self)
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Save & Apply", self)
        save_btn.clicked.connect(self.on_save)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        
    def on_save(self):
        # Update config dictionary
        self.config["fixed_overtime_days"] = self.spin_ot_days.value()
        
        # Handle string or float for leave / late days
        def parse_days_cfg(val):
            val = val.strip()
            if val == "calendar_days":
                return "calendar_days"
            try:
                return float(val)
            except ValueError:
                return val # save as string if they enter something else
                
        self.config["fixed_unpaid_leave_days"] = parse_days_cfg(self.txt_unpaid_days_cfg.text())
        self.config["fixed_late_hours_days"] = parse_days_cfg(self.txt_late_days_cfg.text())
        
        self.config["overtime_rates"] = {
            "weekday": self.spin_rate_weekday.value(),
            "weekend": self.spin_rate_weekend.value(),
            "public_holiday": self.spin_rate_holiday.value()
        }

        if "pcb" not in self.config:
            self.config["pcb"] = {}
        if "reliefs" not in self.config["pcb"]:
            self.config["pcb"]["reliefs"] = {}
            
        self.config["pcb"]["reliefs"]["self"] = self.spin_relief_self.value()
        self.config["pcb"]["reliefs"]["spouse"] = self.spin_relief_spouse.value()
        self.config["pcb"]["reliefs"]["child"] = self.spin_relief_child.value()
        self.config["pcb"]["reliefs"]["epf"] = self.spin_relief_epf.value()

        # Push the edited config back into the global collection, then persist all
        self.configs["config"] = self.config

        try:
            save_all_config(self.configs)
            QMessageBox.information(self, "Success", "Configuration successfully saved and applied.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save configuration: {e}")


class MainWindow(QMainWindow):
    """
    The main window for the Malaysian Salary Calculator.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Malaysian Salary, Statutory & PCB Calculator")
        self.resize(1300, 880)
        self.setup_ui()
        self.apply_theme()
        
        # Internal cache of latest calculation results
        self.latest_results = None
        
        # Trigger initial calculation with default inputs
        self.on_calculate()

    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0F172A;
            }
            QWidget {
                font-family: 'Arial';
                color: #F8FAFC;
            }
            QLabel {
                font-size: 15px;
                font-weight: 500;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #1E293B;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 7px 12px;
                color: #F8FAFC;
                font-size: 15px;
                selection-background-color: #3B82F6;
            }
            QLineEdit:hover, QComboBox:hover, QSpinBox:hover {
                border: 1px solid #64748B;
                background-color: #243349;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid #3B82F6;
                background-color: #1E293B;
            }
            QCheckBox, QRadioButton {
                font-size: 15px;
                spacing: 8px;
            }
            QCheckBox::indicator, QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
            QGroupBox {
                border: 1px solid #334155;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 14px;
                font-weight: bold;
                font-size: 14px;
                color: #94A3B8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                padding: 0 6px;
                background-color: #0F172A;
            }
            QPushButton {
                background-color: #3B82F6;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 9px 18px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
            QPushButton:pressed {
                background-color: #1D4ED8;
            }
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QAbstractScrollArea::viewport {
                background-color: transparent;
                border: none;
            }
        """)

    def setup_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(16)
        
        # --- LEFT PANEL: Input Form ---
        input_scroll = QScrollArea(self)
        input_scroll.setWidgetResizable(True)
        input_scroll.setFrameShape(QFrame.Shape.NoFrame)
        input_scroll.setStyleSheet("""
            QScrollArea { background-color: #0F172A; border: none; }
            QAbstractScrollArea::viewport { background-color: #0F172A; border: none; }
        """)
        
        input_widget = QWidget(self)
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(10)
        
        title_label = QLabel("Salary Parameters", self)
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #38BDF8; letter-spacing: 0.3px;")
        title_label.setContentsMargins(0, 0, 0, 6)
        input_layout.addWidget(title_label)

        # Employment type toggle (Part Timer vs Full Timer)
        self.chk_part_timer = QCheckBox("Part Timer (no EPF / SOCSO / EIS / PCB)", self)
        self.chk_part_timer.setChecked(False)
        chk_layout = QHBoxLayout()
        chk_layout.setContentsMargins(10, 0, 0, 0)
        chk_layout.addWidget(self.chk_part_timer)
        input_layout.addLayout(chk_layout)

        self.input_form = QFormLayout()
        self.input_form.setSpacing(9)
        self.input_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.input_form.setVerticalSpacing(9)

        # Track which widgets belong to each mode for visibility toggling
        self.fulltimer_fields = []
        self.parttimer_fields = []
        self.fulltimer_groups = []

        # Double Validator for currency/hours
        double_validator = QDoubleValidator(0.0, 9999999.99, 4, self)
        double_validator.setNotation(QDoubleValidator.Notation.StandardNotation)

        # Month and Year on a single compact row
        now = datetime.datetime.now()

        month_validator = QIntValidator(1, 12, self)
        self.txt_month = QLineEdit(self)
        self.txt_month.setValidator(month_validator)
        self.txt_month.setText(str(now.month))
        self.txt_month.setPlaceholderText("MM")
        self.txt_month.setFixedWidth(48)

        year_validator = QIntValidator(2000, 2100, self)
        self.txt_year = QLineEdit(self)
        self.txt_year.setValidator(year_validator)
        self.txt_year.setText(str(now.year))
        self.txt_year.setPlaceholderText("YYYY")
        self.txt_year.setFixedWidth(70)

        period_row = QHBoxLayout()
        period_row.setSpacing(4)
        period_row.addWidget(self.txt_month)
        period_row.addWidget(QLabel("/"))
        period_row.addWidget(self.txt_year)
        period_row.addStretch(1)
        self.input_form.addRow("Period (Month/Year):", period_row)

        # Basic Salary Inputs
        self.txt_base_salary = QLineEdit(self)
        self.txt_base_salary.setValidator(double_validator)
        self.txt_base_salary.setText("0")
        self.txt_base_salary.setPlaceholderText("Enter base monthly wages")
        self.input_form.addRow("Base Monthly Salary (RM):", self.txt_base_salary)
        self.fulltimer_fields.append(self.txt_base_salary)

        # Overtime inputs (multi-field)
        self.txt_ot_weekday = QLineEdit(self)
        self.txt_ot_weekday.setValidator(double_validator)
        self.txt_ot_weekday.setText("0")
        self.txt_ot_weekday.setPlaceholderText("Hours (Weekday 1.5x)")
        self.input_form.addRow("Overtime Weekday (Hours):", self.txt_ot_weekday)
        self.fulltimer_fields.append(self.txt_ot_weekday)

        self.txt_ot_weekend = QLineEdit(self)
        self.txt_ot_weekend.setValidator(double_validator)
        self.txt_ot_weekend.setText("0")
        self.txt_ot_weekend.setPlaceholderText("Hours (Weekend 2.0x)")
        self.input_form.addRow("Overtime Weekend (Hours):", self.txt_ot_weekend)
        self.fulltimer_fields.append(self.txt_ot_weekend)

        self.txt_ot_holiday = QLineEdit(self)
        self.txt_ot_holiday.setValidator(double_validator)
        self.txt_ot_holiday.setText("0.0")
        self.txt_ot_holiday.setPlaceholderText("Hours (Holiday 3.0x)")
        self.input_form.addRow("Overtime Public Holiday (Hours):", self.txt_ot_holiday)
        self.fulltimer_fields.append(self.txt_ot_holiday)

        # Deductions
        self.txt_late_hours = QLineEdit(self)
        self.txt_late_hours.setValidator(double_validator)
        self.txt_late_hours.setText("0")
        self.txt_late_hours.setPlaceholderText("Hours late")
        self.input_form.addRow("Late Deduction (Hours):", self.txt_late_hours)
        self.fulltimer_fields.append(self.txt_late_hours)

        self.txt_unpaid_leave = QLineEdit(self)
        self.txt_unpaid_leave.setValidator(double_validator)
        self.txt_unpaid_leave.setText("0")
        self.txt_unpaid_leave.setPlaceholderText("Hours unpaid leave")
        self.input_form.addRow("Unpaid Leave (Hours):", self.txt_unpaid_leave)
        self.fulltimer_fields.append(self.txt_unpaid_leave)

        # Additions
        self.txt_taxable_additional_income = QLineEdit(self)
        self.txt_taxable_additional_income.setValidator(double_validator)
        self.txt_taxable_additional_income.setText("0")
        self.txt_taxable_additional_income.setPlaceholderText("Subject to EPF/SOCSO/EIS & PCB")
        self.input_form.addRow("Taxable Additional Income (RM):", self.txt_taxable_additional_income)
        self.fulltimer_fields.append(self.txt_taxable_additional_income)

        self.txt_nontax_additional_income = QLineEdit(self)
        self.txt_nontax_additional_income.setValidator(double_validator)
        self.txt_nontax_additional_income.setText("0")
        self.txt_nontax_additional_income.setPlaceholderText("Added to nett only")
        self.input_form.addRow("Non-Taxable Additional Income (RM):", self.txt_nontax_additional_income)
        self.fulltimer_fields.append(self.txt_nontax_additional_income)

        # --- Part Timer fields (hidden until toggled) ---
        self.txt_pt_hours = QLineEdit(self)
        self.txt_pt_hours.setValidator(double_validator)
        self.txt_pt_hours.setText("0")
        self.txt_pt_hours.setPlaceholderText("Total hours worked")
        self.input_form.addRow("Total Working Hours:", self.txt_pt_hours)
        self.parttimer_fields.append(self.txt_pt_hours)

        self.txt_pt_rate = QLineEdit(self)
        self.txt_pt_rate.setValidator(double_validator)
        self.txt_pt_rate.setText("0")
        self.txt_pt_rate.setPlaceholderText("Hourly wage")
        self.input_form.addRow("Hourly Rate (RM):", self.txt_pt_rate)
        self.parttimer_fields.append(self.txt_pt_rate)

        self.txt_pt_additional = QLineEdit(self)
        self.txt_pt_additional.setValidator(double_validator)
        self.txt_pt_additional.setText("0")
        self.txt_pt_additional.setPlaceholderText("Allowances / bonuses")
        self.input_form.addRow("Additional Income (RM):", self.txt_pt_additional)
        self.parttimer_fields.append(self.txt_pt_additional)

        # Hide part-timer fields initially (full timer is the default)
        for w in self.parttimer_fields:
            w.setVisible(False)
            lbl = self.input_form.labelForField(w)
            if lbl:
                lbl.setVisible(False)

        input_layout.addLayout(self.input_form)
        
        # --- Marital & Family Status Section ---
        family_group = QGroupBox("Marital & Family Status", self)
        family_layout = QFormLayout(family_group)
        family_layout.setSpacing(5)
        family_layout.setContentsMargins(10, 8, 10, 8)
        
        self.cmb_marital = QComboBox(self)
        self.cmb_marital.addItems(["Single", "Married"])
        self.cmb_marital.setCurrentText("Single")
        family_layout.addRow("Marital Status:", self.cmb_marital)
        
        self.chk_spouse_relief = QCheckBox("Spouse has no income / claim spouse relief", self)
        self.chk_spouse_relief.setChecked(True)
        family_layout.addRow("Spouse Eligible:", self.chk_spouse_relief)
        
        children_validator = QIntValidator(0, 20, self)
        self.txt_children = QLineEdit(self)
        self.txt_children.setValidator(children_validator)
        self.txt_children.setText("0")
        self.txt_children.setPlaceholderText("0–20")
        family_layout.addRow("Number of Children:", self.txt_children)
        
        input_layout.addWidget(family_group)
        self.fulltimer_groups.append(family_group)
        
        # Enable/Disable spouse relief checkbox based on Marital status selection
        self.cmb_marital.currentTextChanged.connect(
            lambda val: self.chk_spouse_relief.setEnabled(val == "Married")
        )
        
        # --- SOCSO Category Section ---
        socso_group = QGroupBox("SOCSO Contribution Category", self)
        socso_layout = QVBoxLayout(socso_group)
        socso_layout.setSpacing(4)
        socso_layout.setContentsMargins(10, 8, 10, 8)
        
        self.radio_socso_cat1 = QRadioButton("First Category (Employee < 60 years old)", self)
        self.radio_socso_cat1.setChecked(True)
        self.radio_socso_cat2 = QRadioButton("Second Category (Employee >= 60 years old)", self)
        
        self.socso_bg = QButtonGroup(self)
        self.socso_bg.addButton(self.radio_socso_cat1, 1)
        self.socso_bg.addButton(self.radio_socso_cat2, 2)
        
        socso_layout.addWidget(self.radio_socso_cat1)
        socso_layout.addWidget(self.radio_socso_cat2)

        self.chk_socso_injury = QCheckBox("Include Non-Employment Injury Scheme", self)
        self.chk_socso_injury.setChecked(False)
        socso_layout.addWidget(self.chk_socso_injury)
        
        input_layout.addWidget(socso_group)
        self.fulltimer_groups.append(socso_group)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_calculate = QPushButton("Calculate Salary", self)
        self.btn_calculate.clicked.connect(lambda: self.on_calculate(show_errors=True))
        
        self.btn_view_config = QPushButton("View Configs", self)
        self.btn_view_config.setObjectName("outlineBtn")
        self.btn_view_config.setStyleSheet("""
            QPushButton#outlineBtn {
                background-color: transparent;
                border: 1px solid #475569;
                color: #94A3B8;
            }
            QPushButton#outlineBtn:hover {
                background-color: #1E293B;
                color: #F8FAFC;
            }
        """)
        self.btn_view_config.clicked.connect(self.on_view_configs)
        
        btn_layout.addWidget(self.btn_calculate, 2)
        btn_layout.addWidget(self.btn_view_config, 1)
        input_layout.addLayout(btn_layout)
        input_layout.addStretch(1)
        
        # --- Connect all input widgets to auto-calculate on change ---
        self.txt_month.textChanged.connect(self.on_calculate)
        self.txt_year.textChanged.connect(self.on_calculate)
        self.txt_base_salary.textChanged.connect(self.on_calculate)
        self.txt_ot_weekday.textChanged.connect(self.on_calculate)
        self.txt_ot_weekend.textChanged.connect(self.on_calculate)
        self.txt_ot_holiday.textChanged.connect(self.on_calculate)
        self.txt_late_hours.textChanged.connect(self.on_calculate)
        self.txt_unpaid_leave.textChanged.connect(self.on_calculate)
        self.txt_taxable_additional_income.textChanged.connect(self.on_calculate)
        self.txt_nontax_additional_income.textChanged.connect(self.on_calculate)
        self.cmb_marital.currentTextChanged.connect(self.on_calculate)
        self.chk_spouse_relief.toggled.connect(self.on_calculate)
        self.txt_children.textChanged.connect(self.on_calculate)
        self.socso_bg.idToggled.connect(self.on_calculate)
        self.chk_socso_injury.toggled.connect(self.on_calculate)
        self.chk_part_timer.toggled.connect(self.update_mode)
        self.txt_pt_hours.textChanged.connect(self.on_calculate)
        self.txt_pt_rate.textChanged.connect(self.on_calculate)
        self.txt_pt_additional.textChanged.connect(self.on_calculate)
        
        input_scroll.setWidget(input_widget)
        main_layout.addWidget(input_scroll, 1)
        
        # --- RIGHT PANEL: Calculation Results Dashboard ---
        results_widget = QWidget(self)
        results_layout = QVBoxLayout(results_widget)
        results_layout.setContentsMargins(0, 0, 0, 0)
        results_layout.setSpacing(10)
        
        # 1. Nett Salary Card (Highlight)
        self.nett_card = QFrame(self)
        self.nett_card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1E3A8A, stop:1 #0F766E);
                border-radius: 12px;
            }
            QLabel {
                color: #F8FAFC;
                background-color: transparent;
            }
        """)
        nett_card_layout = QVBoxLayout(self.nett_card)
        nett_card_layout.setContentsMargins(20, 16, 20, 16)
        nett_card_layout.setSpacing(4)
        nett_card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        nett_title = QLabel("NETT MONTHLY SALARY", self.nett_card)
        nett_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #93C5FD; letter-spacing: 1px;")
        
        self.lbl_nett_val = QLabel("RM 0.00", self.nett_card)
        self.lbl_nett_val.setStyleSheet("font-size: 32px; font-weight: 800; color: #FFFFFF;")
        
        nett_card_layout.addWidget(nett_title)
        nett_card_layout.addWidget(self.lbl_nett_val)
        results_layout.addWidget(self.nett_card)
        
        # 2. Main Breakdown Table
        self.breakdown_group = QGroupBox("Payroll Breakdown", self)
        self.breakdown_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.breakdown_layout = QVBoxLayout(self.breakdown_group)
        self.breakdown_layout.setSpacing(6)
        self.breakdown_layout.setContentsMargins(10, 8, 10, 8)
        self.breakdown_table = None  # created by rebuild_breakdown()

        results_layout.addWidget(self.breakdown_group)

        # Build the breakdown table for the default (full timer) mode
        self.rebuild_breakdown(FULLTIMER_BREAKDOWN_ROWS)

        
        # Export PDF button
        self.btn_export = QPushButton("Export PDF Pay Slip", self)
        self.btn_export.setObjectName("secondaryBtn")
        self.btn_export.setStyleSheet("""
            QPushButton#secondaryBtn {
                background-color: #0D9488;
            }
            QPushButton#secondaryBtn:hover {
                background-color: #0F766E;
            }
            QPushButton#secondaryBtn:pressed {
                background-color: #115E59;
            }
        """)
        self.btn_export.clicked.connect(self.on_export_pdf)
        results_layout.addWidget(self.btn_export)
        
        main_layout.addWidget(results_widget, 1)

    def rebuild_breakdown(self, rows):
        """(Re)build the payroll breakdown table from a list of (label, merged) tuples."""
        if self.breakdown_table:
            self.breakdown_layout.removeWidget(self.breakdown_table)
            self.breakdown_table.deleteLater()
            self.breakdown_table = None

        self._breakdown_cells = {}
        nrows = len(rows)
        self.breakdown_table = QTableWidget(nrows, 3, self)
        self.breakdown_table.setHorizontalHeaderLabels(["Description", "Employee (RM)", "Employer (RM)"])
        self.breakdown_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.breakdown_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.breakdown_table.verticalHeader().setVisible(False)
        hh = self.breakdown_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.breakdown_table.setShowGrid(True)
        self.breakdown_table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                gridline-color: #334155;
                font-size: 15px;
                border: none;
            }
            QTableWidget::item {
                padding: 11px 10px;
            }
            QTableWidget::item:selected, QTableWidget::item:hover {
                background-color: #1E293B;
            }
            QHeaderView::section {
                background-color: #1E293B;
                color: #94A3B8;
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
                border: none;
                border-bottom: 1px solid #334155;
            }
        """)

        deduction_labels = {
            "Late Deduction", "Unpaid Leave Deduction",
            "EPF (Statutory)", "SOCSO (Statutory)", "EIS (Statutory)",
            "PCB Monthly Tax Deduction"
        }
        red_fg = QColor("#EF4444")
        label_fg = QColor("#CBD5E1")
        base_font = QFont("Arial", 15)
        bold_font = QFont("Arial", 15)
        bold_font.setBold(True)

        for i, (label, merged) in enumerate(rows):
            item_label = QTableWidgetItem(label)
            item_label.setFlags(item_label.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_label.setFont(bold_font)
            item_label.setForeground(label_fg)
            self.breakdown_table.setItem(i, 0, item_label)

            if merged:
                val_item = QTableWidgetItem("RM 0.00")
                val_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                val_item.setFlags(val_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                val_item.setFont(base_font)
                if label in deduction_labels:
                    val_item.setForeground(red_fg)
                if label in ("Gross Salary", "Nett Take-Home Salary"):
                    val_item.setFont(bold_font)
                self.breakdown_table.setItem(i, 1, val_item)
                self.breakdown_table.setSpan(i, 1, 1, 2)
                self._breakdown_cells[label] = val_item
            else:
                emp = QTableWidgetItem("RM 0.00")
                emp.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                emp.setFlags(emp.flags() & ~Qt.ItemFlag.ItemIsEditable)
                emp.setFont(base_font)
                empr = QTableWidgetItem("RM 0.00")
                empr.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                empr.setFlags(empr.flags() & ~Qt.ItemFlag.ItemIsEditable)
                empr.setFont(base_font)
                if label in deduction_labels:
                    emp.setForeground(red_fg)
                    empr.setForeground(red_fg)
                self.breakdown_table.setItem(i, 1, emp)
                self.breakdown_table.setItem(i, 2, empr)
                self._breakdown_cells[label] = (emp, empr)

        self.breakdown_layout.addWidget(self.breakdown_table)

        # Set consistent row heights
        row_height = self.breakdown_table.verticalHeader().defaultSectionSize()
        for i in range(nrows):
            self.breakdown_table.setRowHeight(i, max(row_height, 42))

    def update_mode(self):
        """Toggle field visibility between full-timer and part-timer input sets."""
        is_pt = self.chk_part_timer.isChecked()

        for w in self.fulltimer_fields:
            w.setVisible(not is_pt)
            lbl = self.input_form.labelForField(w)
            if lbl:
                lbl.setVisible(not is_pt)

        for g in self.fulltimer_groups:
            g.setVisible(not is_pt)

        for w in self.parttimer_fields:
            w.setVisible(is_pt)
            lbl = self.input_form.labelForField(w)
            if lbl:
                lbl.setVisible(is_pt)

        if is_pt:
            self.rebuild_breakdown(PARTTIMER_BREAKDOWN_ROWS)
        else:
            self.rebuild_breakdown(FULLTIMER_BREAKDOWN_ROWS)

        self.on_calculate()

    def on_calculate(self, show_errors=False):
        """
        Gathers inputs and executes the calculation engine.
        When called by auto-calculate signals, show_errors is False to silently
        ignore transient parse errors (e.g., empty field while user is typing).
        """
        try:
            # Parse period (shared by both modes)
            month = int(self.txt_month.text() or str(datetime.datetime.now().month))
            year = int(self.txt_year.text() or str(datetime.datetime.now().year))
            month = max(1, min(12, month))  # clamp to valid range

            is_part_timer = self.chk_part_timer.isChecked()

            if is_part_timer:
                pt_hours = Decimal(self.txt_pt_hours.text() or "0")
                pt_rate = Decimal(self.txt_pt_rate.text() or "0")
                pt_add = Decimal(self.txt_pt_additional.text() or "0")

                res = calculate_salary_package(
                    is_part_timer=True,
                    total_working_hours=pt_hours,
                    hourly_rate=pt_rate,
                    taxable_additional_income=pt_add,
                    month=month,
                    year=year
                )
            else:
                base_sal = Decimal(self.txt_base_salary.text() or "0")
                ot_weekday = Decimal(self.txt_ot_weekday.text() or "0")
                ot_weekend = Decimal(self.txt_ot_weekend.text() or "0")
                ot_holiday = Decimal(self.txt_ot_holiday.text() or "0")
                late_hrs = Decimal(self.txt_late_hours.text() or "0")
                unpaid_days = Decimal(self.txt_unpaid_leave.text() or "0")
                taxable_add_inc = Decimal(self.txt_taxable_additional_income.text() or "0")
                nontax_add_inc = Decimal(self.txt_nontax_additional_income.text() or "0")

                marital = self.cmb_marital.currentText()
                spouse_elg = self.chk_spouse_relief.isChecked() if marital == "Married" else False
                child_cnt = int(self.txt_children.text() or "0")

                socso_cat = "first_category" if self.radio_socso_cat1.isChecked() else "second_category"
                include_injury = self.chk_socso_injury.isChecked()

                res = calculate_salary_package(
                    monthly_salary=base_sal,
                    overtime_weekday_hours=ot_weekday,
                    overtime_weekend_hours=ot_weekend,
                    overtime_holiday_hours=ot_holiday,
                    late_hours=late_hrs,
                    unpaid_leave_days=unpaid_days,
                    taxable_additional_income=taxable_add_inc,
                    nontaxable_additional_income=nontax_add_inc,
                    socso_category=socso_cat,
                    include_non_employment_injury=include_injury,
                    spouse_eligible=spouse_elg,
                    children_count=child_cnt,
                    marital_status=marital,
                    month=month,
                    year=year
                )

            # Store results cache
            self.latest_results = res
            
            # Update UI outputs
            self.lbl_nett_val.setText(f"RM {res['nett_salary']:,.2f}")

            cells = self._breakdown_cells
            if res.get("is_part_timer"):
                cells["Nett Take-Home Salary"].setText(f"RM {res['nett_salary']:,.2f}")
            else:
                stat = res["statutory"]
                cells["Gross Salary"].setText(f"RM {res['gross_salary']:,.2f}")
                cells["Late Deduction"].setText(
                    f"-RM {res['deductions']['late_deduction']:,.2f}"
                )
                cells["Unpaid Leave Deduction"].setText(
                    f"-RM {res['deductions']['unpaid_leave_deduction']:,.2f}"
                )
                cells["EPF (Statutory)"][0].setText(f"RM {stat['epf_employee']:,.2f}")
                cells["EPF (Statutory)"][1].setText(f"RM {stat['epf_employer']:,.2f}")
                cells["SOCSO (Statutory)"][0].setText(f"RM {stat['socso_employee']:,.2f}")
                cells["SOCSO (Statutory)"][1].setText(f"RM {stat['socso_employer']:,.2f}")
                cells["EIS (Statutory)"][0].setText(f"RM {stat['eis_employee']:,.2f}")
                cells["EIS (Statutory)"][1].setText(f"RM {stat['eis_employer']:,.2f}")
                cells["PCB Monthly Tax Deduction"].setText(f"RM {stat['pcb']:,.2f}")
                cells["Nett Take-Home Salary"].setText(f"RM {res['nett_salary']:,.2f}")
            
        except Exception as e:
            if show_errors:
                QMessageBox.critical(self, "Calculation Error", f"Failed to compute payroll values: {e}")

    def on_view_configs(self):
        dialog = ConfigEditorDialog(self)
        if dialog.exec() == QDialog.accepted:
            self.on_calculate()

    def on_export_pdf(self):
        """
        Generates a premium HTML payslip and prints it to PDF.
        """
        if not self.latest_results:
            QMessageBox.warning(self, "Export Warning", "Please execute a valid calculation first.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Pay Slip", "", "PDF Files (*.pdf)"
        )
        if not file_path:
            return
            
        res = self.latest_results

        if res.get("is_part_timer"):
            QMessageBox.information(
                self, "Export Unavailable",
                "PDF export is only available for full-timer payslips."
            )
            return

        inputs = res["inputs"]
        additions = res["additions"]
        deductions = res["deductions"]
        stat = res["statutory"]
        
        # Build premium HTML contents
        html_content = f"""
        <!DOCTYPE html>
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
                <p class="company-name">DEMO MALAYSIA ENTERPRISE</p>
                <span class="payslip-title">Official Pay Slip</span>
            </div>
            
            <table class="meta-table">
                <tr>
                    <td class="text-bold">Employee Status:</td>
                    <td>{inputs['socso_category'].replace('_', ' ').title()}</td>
                    <td class="text-bold">Marital Status:</td>
                    <td>{inputs['marital']}</td>
                </tr>
                <tr>
                    <td class="text-bold">Spouse Relief:</td>
                    <td>{'Claimed' if inputs['spouse_eligible'] else 'None'}</td>
                    <td class="text-bold">Children Count:</td>
                    <td>{inputs['children_count']}</td>
                </tr>
                <tr>
                    <td class="text-bold">Pay Period:</td>
                    <td>{calendar.month_name[inputs['month']]} {inputs['year']}</td>
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
                        <td class="right">{inputs['monthly_salary']:,.2f}</td>
                        <td class="right">-</td>
                    </tr>
                    <tr>
                        <td>Weekday Overtime ({inputs['overtime_weekday_hours']} hrs)</td>
                        <td class="right">{additions['overtime_weekday_pay']:,.2f}</td>
                        <td class="right">-</td>
                    </tr>
                    <tr>
                        <td>Weekend Overtime ({inputs['overtime_weekend_hours']} hrs)</td>
                        <td class="right">{additions['overtime_weekend_pay']:,.2f}</td>
                        <td class="right">-</td>
                    </tr>
                    <tr>
                        <td>Public Holiday Overtime ({inputs['overtime_holiday_hours']} hrs)</td>
                        <td class="right">{additions['overtime_holiday_pay']:,.2f}</td>
                        <td class="right">-</td>
                    </tr>
                    <tr>
                        <td>Taxable Additional Income</td>
                        <td class="right">{additions['taxable_additional_income']:,.2f}</td>
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
                        <td>Late Hours Deduction ({inputs['late_hours']} hrs)</td>
                        <td class="right" style="color: #EF4444;">-{deductions['late_deduction']:,.2f}</td>
                        <td class="right">-</td>
                    </tr>
                    <tr>
                        <td>Unpaid Leave Deduction ({inputs['unpaid_leave_days']} days)</td>
                        <td class="right" style="color: #EF4444;">-{deductions['unpaid_leave_deduction']:,.2f}</td>
                        <td class="right">-</td>
                    </tr>
                    
                    <tr class="total">
                        <td>GROSS SALARY</td>
                        <td class="right">{res['gross_salary']:,.2f}</td>
                        <td class="right">-</td>
                    </tr>
                    
                    <tr>
                        <td>EPF Contribution</td>
                        <td class="right" style="color: #EF4444;">-{stat['epf_employee']:,.2f}</td>
                        <td class="right">{stat['epf_employer']:,.2f}</td>
                    </tr>
                    <tr>
                        <td>SOCSO Contribution</td>
                        <td class="right" style="color: #EF4444;">-{stat['socso_employee']:,.2f}</td>
                        <td class="right">{stat['socso_employer']:,.2f}</td>
                    </tr>
                    <tr>
                        <td>EIS Contribution</td>
                        <td class="right" style="color: #EF4444;">-{stat['eis_employee']:,.2f}</td>
                        <td class="right">{stat['eis_employer']:,.2f}</td>
                    </tr>
                    <tr>
                        <td>PCB Monthly Tax Deduction</td>
                        <td class="right" style="color: #EF4444;">-{stat['pcb']:,.2f}</td>
                        <td class="right">-</td>
                    </tr>
                    
                    <tr>
                        <td>Non-Taxable Additional Income</td>
                        <td class="right" style="color: #10B981;">+{additions['nontaxable_additional_income']:,.2f}</td>
                        <td class="right">-</td>
                    </tr>
                    
                    <tr class="nett-total">
                        <td>NETT TAKE-HOME SALARY</td>
                        <td class="right">RM {res['nett_salary']:,.2f}</td>
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
        
        try:
            doc = QTextDocument()
            doc.setHtml(html_content)
            
            writer = QPdfWriter(file_path)
            # Set resolution to screen-equivalent DPI so CSS px sizes render correctly
            writer.setResolution(96)
            # Setup Page layout
            writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            
            # Print document using standard PySide6 print
            doc.print_(writer)
            
            QMessageBox.information(
                self, "Export Success", f"Pay Slip successfully saved as PDF:\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export PDF: {e}")
