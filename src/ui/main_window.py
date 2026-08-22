import datetime
import logging
import os
from decimal import Decimal

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QDoubleValidator,
    QFont,
    QIcon,
    QIntValidator,
)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.config_loader import get_resource_path
from core.payroll_engine import PayrollEngine, PayrollInput
from services.payslip_exporter import PayslipExporter
from services.update_checker import UpdateCheckerThread
from services.update_downloader import UpdateDownloaderThread, apply_update_and_restart
from version import __version__

# Rows shown in the payroll breakdown table for each employment mode.
# Each entry is (label, merged?) where merged rows span the Employee + Employer columns.
FULLTIMER_BREAKDOWN_ROWS = [
    ("Gross Salary", True),
    ("Weekdays OT", True),
    ("Weekend OT", True),
    ("Public Holiday OT", True),
    ("Late Deduction", True),
    ("Unpaid Leave Deduction", True),
    ("EPF (Statutory)", False),
    ("SOCSO (Statutory)", False),
    ("EIS (Statutory)", False),
    ("PCB Monthly Tax Deduction", True),
]

PARTTIMER_BREAKDOWN_ROWS = [
    ("Nett Take-Home Salary", True),
]

from ui.dialogs.config_dialog import ConfigEditorDialog


class MainWindow(QMainWindow):
    """
    The main window for the Malaysian Salary Calculator.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Malaysian Salary Calculator v{__version__}")
        self.resize(1300, 880)

        icon_path = get_resource_path("icon/app_icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.current_mode = "dark"
        
        self.setup_ui()
        self.apply_theme()
        
        # Internal cache of latest calculation results
        self.latest_results = None
        
        # Trigger initial calculation with default inputs
        self.on_calculate()

        # Check for GitHub releases in the background
        self.update_checker = UpdateCheckerThread(parent=self)
        self.update_checker.update_available.connect(self.on_update_available)
        self.update_checker.start()

    def apply_theme(self, target=None, mode=None):
        if target is None:
            target = self
        if mode is None:
            mode = getattr(self, "current_mode", "dark")
        MainWindow.apply_theme_to(target, mode)

    @staticmethod
    def apply_theme_to(target, mode: str = "dark"):
        """
        Loads and applies QSS stylesheets directly onto target widget/dialog.
        """
        mode_name = mode.lower() if mode else "dark"
        style_path = get_resource_path(f"assets/styles/{mode_name}.qss")
        assets_dir = get_resource_path("assets").replace("\\", "/")

        try:
            with open(style_path, "r", encoding="utf-8") as f:
                qss_content = f.read()

            qss_formatted = qss_content.replace("{assets_dir}", assets_dir)
            target.setStyleSheet(qss_formatted)
        except Exception as e:
            logging.error(f"Failed to apply theme '{mode}' from {style_path}: {e}")

    def setup_ui(self):
        # --- TOP HEADER BAR ---
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 10)
        header_layout.setSpacing(8)
        
        self.app_title_lbl = QLabel("Malaysian Salary Calculator")
        self.app_title_lbl.setObjectName("appTitle")
        
        self.version_badge = QLabel(f"v{__version__}")
        self.version_badge.setObjectName("versionBadge")
        
        self.btn_view_config = QPushButton("⚙️ Configs", self)
        self.btn_view_config.setObjectName("outlineBtn")
        self.btn_view_config.clicked.connect(self.on_view_configs)

        self.btn_toggle_mode = QPushButton("🌙 Dark", self)
        self.btn_toggle_mode.setObjectName("toggleModeBtn")
        self.btn_toggle_mode.setCheckable(True)
        self.btn_toggle_mode.setChecked(True)
        self.btn_toggle_mode.clicked.connect(self.on_mode_toggle)
        
        header_layout.addWidget(self.app_title_lbl)
        header_layout.addWidget(self.version_badge)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_view_config)
        header_layout.addWidget(self.btn_toggle_mode)
        
        # We will wrap the main content in a VBox to include the header
        wrapper_widget = QWidget(self)
        self.setCentralWidget(wrapper_widget)
        
        wrapper_layout = QVBoxLayout(wrapper_widget)
        wrapper_layout.setContentsMargins(12, 12, 12, 12)
        wrapper_layout.addLayout(header_layout)
        
        # --- UPDATE NOTIFICATION BANNER ---
        self.update_banner = QFrame(self)
        self.update_banner.setObjectName("updateBanner")
        self.update_banner.setVisible(False)
        banner_layout = QHBoxLayout(self.update_banner)
        banner_layout.setContentsMargins(14, 8, 14, 8)
        banner_layout.setSpacing(12)
        
        self.lbl_update_msg = QLabel("🎉 A new release is available on GitHub!", self.update_banner)
        self.btn_download_update = QPushButton("⬇️ Download Update", self.update_banner)
        self.btn_download_update.setObjectName("primaryBtn")
        self.btn_download_update.clicked.connect(self.on_download_update_clicked)
        self.btn_dismiss_update = QPushButton("✕", self.update_banner)
        self.btn_dismiss_update.setObjectName("dismissBannerBtn")
        self.btn_dismiss_update.setFixedSize(28, 28)
        self.btn_dismiss_update.setToolTip("Dismiss notification")
        self.btn_dismiss_update.clicked.connect(lambda: self.update_banner.setVisible(False))

        # Progress widgets for background downloading
        self.lbl_download_status = QLabel("Downloading...", self.update_banner)
        self.lbl_download_status.setObjectName("downloadStatusLabel")
        self.lbl_download_status.setVisible(False)

        self.update_progress_bar = QProgressBar(self.update_banner)
        self.update_progress_bar.setObjectName("updateProgressBar")
        self.update_progress_bar.setRange(0, 100)
        self.update_progress_bar.setValue(0)
        self.update_progress_bar.setFixedHeight(16)
        self.update_progress_bar.setVisible(False)
        
        banner_layout.addWidget(self.lbl_update_msg)
        banner_layout.addWidget(self.lbl_download_status)
        banner_layout.addWidget(self.update_progress_bar, 1)
        banner_layout.addStretch()
        banner_layout.addWidget(self.btn_download_update)
        banner_layout.addWidget(self.btn_dismiss_update)

        wrapper_layout.addWidget(self.update_banner)
        
        # Now create the split layout
        main_layout = QHBoxLayout()
        main_layout.setSpacing(16)
        wrapper_layout.addLayout(main_layout, 1)
        
        # --- LEFT PANEL: Input Form (Card Container) ---
        left_card = QFrame(self)
        left_card.setObjectName("leftCard")
        left_card_layout = QVBoxLayout(left_card)
        left_card_layout.setContentsMargins(12, 12, 12, 12)

        input_scroll = QScrollArea(left_card)
        input_scroll.setObjectName("inputScroll")
        input_scroll.setWidgetResizable(True)
        input_scroll.setFrameShape(QFrame.Shape.NoFrame)
        input_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        input_widget = QWidget(input_scroll)
        input_widget.setObjectName("inputWidget")
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(10)
        
        title_label = QLabel("Salary Parameters", self)
        title_label.setObjectName("sectionTitle")
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
        
        # --- Marital & Family Status Section & SOCSO Category Section (Side by Side) ---
        family_socso_layout = QHBoxLayout()
        family_socso_layout.setSpacing(10)

        family_group = QGroupBox("Marital and Family Status", self)
        family_layout = QFormLayout(family_group)
        family_layout.setSpacing(5)
        family_layout.setContentsMargins(10, 8, 10, 8)
        
        self.cmb_marital = QComboBox(self)
        self.cmb_marital.addItems(["Single", "Married"])
        self.cmb_marital.setCurrentText("Single")
        family_layout.addRow("Marital Status:", self.cmb_marital)
        
        self.chk_spouse_relief = QCheckBox("Spouse has no income / claim relief", self)
        self.chk_spouse_relief.setChecked(True)
        family_layout.addRow("Spouse Eligible:", self.chk_spouse_relief)
        
        children_validator = QIntValidator(0, 20, self)
        self.txt_children = QLineEdit(self)
        self.txt_children.setValidator(children_validator)
        self.txt_children.setText("0")
        self.txt_children.setPlaceholderText("0–20")
        family_layout.addRow("Number of Children:", self.txt_children)
        
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
        
        self.radio_socso_cat1 = QRadioButton("First Category (< 60 yrs old)", self)
        self.radio_socso_cat1.setChecked(True)
        self.radio_socso_cat2 = QRadioButton("Second Category (≥ 60 yrs old)", self)
        
        self.socso_bg = QButtonGroup(self)
        self.socso_bg.addButton(self.radio_socso_cat1, 1)
        self.socso_bg.addButton(self.radio_socso_cat2, 2)
        
        socso_layout.addWidget(self.radio_socso_cat1)
        socso_layout.addWidget(self.radio_socso_cat2)

        self.chk_socso_injury = QCheckBox("Include Non-Employment Injury Scheme\n(LINDUNG24)", self)
        self.chk_socso_injury.setChecked(False)
        socso_layout.addWidget(self.chk_socso_injury)
        
        self.fulltimer_groups.append(socso_group)

        # Add both group boxes to horizontal layout
        family_socso_layout.addWidget(family_group, 1)
        family_socso_layout.addWidget(socso_group, 1)
        input_layout.addLayout(family_socso_layout)
        
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
        left_card_layout.addWidget(input_scroll)
        main_layout.addWidget(left_card, 1)
        
        # --- RIGHT PANEL: Calculation Results Dashboard (Card Container) ---
        right_card = QFrame(self)
        right_card.setObjectName("rightCard")
        results_layout = QVBoxLayout(right_card)
        results_layout.setContentsMargins(12, 12, 12, 12)
        results_layout.setSpacing(10)
        
        # 1. Nett Salary Card (Highlight)
        self.nett_card = QFrame(self)
        self.nett_card.setObjectName("nettCard")
        nett_card_layout = QVBoxLayout(self.nett_card)
        nett_card_layout.setContentsMargins(20, 16, 20, 16)
        nett_card_layout.setSpacing(4)
        nett_card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        nett_title = QLabel("NETT MONTHLY SALARY", self.nett_card)
        nett_title.setObjectName("nettTitle")
        
        self.lbl_nett_val = QLabel("RM 0.00", self.nett_card)
        self.lbl_nett_val.setObjectName("nettValue")
        
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
        self.btn_export.setObjectName("primaryBtn")
        self.btn_export.clicked.connect(self.on_export_pdf)
        results_layout.addWidget(self.btn_export)
        
        main_layout.addWidget(right_card, 1)

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

        deduction_labels = {
            "Late Deduction", "Unpaid Leave Deduction",
            "EPF (Statutory)", "SOCSO (Statutory)", "EIS (Statutory)",
            "PCB Monthly Tax Deduction"
        }
        red_fg = QColor("#EF4444")
        base_font = QFont("Arial", 15)
        bold_font = QFont("Arial", 15)
        bold_font.setBold(True)

        for i, (label, merged) in enumerate(rows):
            item_label = QTableWidgetItem(label)
            item_label.setFlags(item_label.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item_label.setFont(bold_font)
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

        row_height = self.breakdown_table.verticalHeader().defaultSectionSize()
        for i in range(nrows):
            self.breakdown_table.setRowHeight(i, max(row_height, 42))

    def on_mode_toggle(self):
        if self.btn_toggle_mode.isChecked():
            self.current_mode = "dark"
            self.btn_toggle_mode.setText("🌙 Dark")
        else:
            self.current_mode = "light"
            self.btn_toggle_mode.setText("☀️ Light")
        self.apply_theme()

    def on_download_update_clicked(self):
        download_url = getattr(self, "download_url", "")
        if not download_url:
            # Fallback to browser if direct asset URL is not found
            url = getattr(self, "release_url", "https://github.com/Lhz0616/malaysia-salary-calculator/releases")
            QDesktopServices.openUrl(QUrl(url))
            return

        # Switch banner to downloading progress mode
        self.lbl_update_msg.setVisible(False)
        self.btn_download_update.setVisible(False)
        self.btn_dismiss_update.setVisible(False)

        self.lbl_download_status.setText("Downloading...")
        self.lbl_download_status.setVisible(True)
        self.update_progress_bar.setValue(0)
        self.update_progress_bar.setVisible(True)

        self.downloader_thread = UpdateDownloaderThread(download_url, parent=self)
        self.downloader_thread.progress.connect(self.on_download_progress)
        self.downloader_thread.download_finished.connect(self.on_download_finished)
        self.downloader_thread.error_occurred.connect(self.on_download_error)
        self.downloader_thread.start()

    def on_download_progress(self, downloaded, total):
        if total > 0:
            percent = int((downloaded / total) * 100)
            self.update_progress_bar.setRange(0, 100)
            self.update_progress_bar.setValue(percent)
            self.lbl_download_status.setText(f"Downloading... ({percent}%)")
        else:
            self.update_progress_bar.setRange(0, 0)
            self.lbl_download_status.setText("Downloading...")

    def on_download_finished(self, installer_path):
        self.lbl_download_status.setText("Applying update and restarting...")
        self.update_progress_bar.setRange(0, 100)
        self.update_progress_bar.setValue(100)
        
        apply_update_and_restart(installer_path)
        QApplication.instance().quit()

    def on_download_error(self, error_msg):
        logging.error(f"Failed to download update: {error_msg}")
        self.lbl_download_status.setVisible(False)
        self.update_progress_bar.setVisible(False)
        
        self.lbl_update_msg.setText("⚠️ Automatic update failed. Click to open browser download.")
        self.lbl_update_msg.setVisible(True)
        self.btn_download_update.setText("🌐 Open Download Page")
        self.btn_download_update.setVisible(True)
        self.btn_dismiss_update.setVisible(True)

    def on_update_available(self, latest_version, release_url, release_notes, download_url=""):
        self.lbl_update_msg.setText(f"🎉 New version {latest_version} is available on GitHub!")
        self.release_url = release_url
        self.download_url = download_url
        
        # Reset banner state
        self.lbl_download_status.setVisible(False)
        self.update_progress_bar.setVisible(False)
        self.lbl_update_msg.setVisible(True)
        self.btn_download_update.setText("⬇️ Download Update")
        self.btn_download_update.setVisible(True)
        self.btn_dismiss_update.setVisible(True)
        self.update_banner.setVisible(True)

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

                inp = PayrollInput(
                    is_part_timer=True,
                    total_working_hours=pt_hours,
                    hourly_rate=pt_rate,
                    taxable_additional_income=pt_add,
                    month=month,
                    year=year
                )
                res = PayrollEngine.default().calculate(inp)
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

                inp = PayrollInput(
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
                res = PayrollEngine.default().calculate(inp)

            # Store results cache
            self.latest_results = res
            
            # Update UI outputs
            self.lbl_nett_val.setText(f"RM {res['nett_salary']:,.2f}")

            cells = self._breakdown_cells
            if res.get("is_part_timer"):
                cells["Nett Take-Home Salary"].setText(f"RM {res['nett_salary']:,.2f}")
            else:
                additions = res["additions"]
                stat = res["statutory"]
                cells["Gross Salary"].setText(f"RM {res['gross_salary']:,.2f}")
                if "Weekdays OT" in cells:
                    cells["Weekdays OT"].setText(f"RM {additions['overtime_weekday_pay']:,.2f}")
                if "Weekend OT" in cells:
                    cells["Weekend OT"].setText(f"RM {additions['overtime_weekend_pay']:,.2f}")
                if "Public Holiday OT" in cells:
                    cells["Public Holiday OT"].setText(f"RM {additions['overtime_holiday_pay']:,.2f}")
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
            
        except Exception as e:
            if show_errors:
                QMessageBox.critical(self, "Calculation Error", f"Failed to compute payroll values: {e}")

    def on_view_configs(self):
        dialog = ConfigEditorDialog(self)
        if dialog.exec() == QDialog.accepted:
            self.on_calculate()

    def on_export_pdf(self):
        """
        Delegates payslip document rendering and PDF export to PayslipExporter.
        """
        if not self.latest_results:
            QMessageBox.warning(self, "Export Warning", "Please execute a valid calculation first.")
            return

        res = self.latest_results
        if res.get("is_part_timer"):
            QMessageBox.information(
                self, "Export Unavailable",
                "PDF export is currently supported for full-timer payslips."
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Pay Slip", "", "PDF Files (*.pdf)"
        )
        if not file_path:
            return

        try:
            PayslipExporter.export_pdf(res, file_path)
            QMessageBox.information(
                self, "Export Success", f"Pay Slip successfully saved as PDF:\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export PDF: {e}")
