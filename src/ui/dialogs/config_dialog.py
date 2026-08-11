from PySide6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.config_loader import get_configs, save_all_config


class ConfigEditorDialog(QDialog):
    """
    Pop-up dialog that allows editing global system configuration JSON parameters.
    Extracted from main_window.py into a modular dialog component.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuration Editor")
        self.resize(550, 480)
        self.current_mode = parent.current_mode if hasattr(parent, 'current_mode') else "dark"

        if parent and hasattr(parent, 'apply_theme'):
            parent.apply_theme(self, mode=self.current_mode)
        else:
            from ui.main_window import MainWindow
            MainWindow.apply_theme_to(self, self.current_mode)

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
        title_lbl.setObjectName("sectionTitle")
        layout.addWidget(title_lbl)

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
        cancel_btn.setObjectName("outlineBtn")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save & Apply", self)
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self.on_save)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def on_save(self):
        self.config["fixed_overtime_days"] = self.spin_ot_days.value()

        def parse_days_cfg(val):
            val = val.strip()
            if val == "calendar_days":
                return "calendar_days"
            try:
                return float(val)
            except ValueError:
                return val

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

        self.configs["config"] = self.config

        try:
            save_all_config(self.configs)
            QMessageBox.information(self, "Success", "Configuration successfully saved and applied.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save configuration: {e}")
