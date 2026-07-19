import logging
import os

ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets")).replace("\\", "/")
CHECK_LIGHT_URL = f"{ASSETS_DIR}/check_light.svg"
CHECK_DARK_URL = f"{ASSETS_DIR}/check_dark.svg"
RADIO_LIGHT_URL = f"{ASSETS_DIR}/radio_light.svg"
RADIO_DARK_URL = f"{ASSETS_DIR}/radio_dark.svg"

# ===================================================================
# THEME: SOFT MATERIAL PAPER (LIGHT & DARK)
# ===================================================================
SOFT_PAPER_LIGHT_QSS = """
QMainWindow, QDialog {{
    background-color: #F8FAFC;
    color: #1E293B;
    font-family: 'Segoe UI', Arial, sans-serif;
}}
QWidget {{
    font-family: 'Segoe UI', Arial, sans-serif;
    color: #1E293B;
}}

QScrollArea, QScrollArea > QWidget, QAbstractScrollArea::viewport, #inputScroll, #inputWidget {{
    background-color: transparent;
    border: none;
}}

QFrame#leftCard, QFrame#rightCard {{
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 14px;
}}

QLabel {{
    font-size: 14px;
    font-weight: 500;
    color: #1E293B;
    background: transparent;
}}
QLabel#appTitle {{
    font-size: 20px;
    font-weight: bold;
    color: #4F46E5;
}}
QLabel#sectionTitle {{
    font-size: 22px;
    font-weight: bold;
    color: #4F46E5;
    letter-spacing: 0.3px;
}}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 7px 12px;
    color: #0F172A;
    font-size: 14px;
    selection-background-color: #6366F1;
    selection-color: #FFFFFF;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1.5px solid #6366F1;
    background-color: #FFFFFF;
}}

QComboBox QAbstractItemView {{
    background-color: #FFFFFF;
    color: #1E293B;
    border: 1px solid #CBD5E1;
    selection-background-color: #EEF2FF;
    selection-color: #4338CA;
    padding: 4px;
}}

QCheckBox, QRadioButton {{
    color: #1E293B;
    background: transparent;
    font-size: 14px;
    font-weight: 500;
    spacing: 8px;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1.5px solid #94A3B8;
    background-color: #FFFFFF;
}}
QCheckBox::indicator {{
    border-radius: 4px;
}}
QRadioButton::indicator {{
    border-radius: 9px;
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: #6366F1;
}}
QCheckBox::indicator:checked {{
    background-color: #FFFFFF;
    border: 1.5px solid #6366F1;
    image: url('{check_light_url}');
}}
QRadioButton::indicator:checked {{
    background-color: #FFFFFF;
    border: 1.5px solid #6366F1;
    image: url('{radio_light_url}');
}}

QGroupBox {{
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    margin-top: 12px;
    padding-top: 14px;
    font-weight: bold;
    font-size: 14px;
    color: #475569;
    background-color: #FFFFFF;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 2px 10px;
    background-color: #EEF2FF;
    border: 1px solid #C7D2FE;
    border-radius: 10px;
    color: #4338CA;
    font-weight: bold;
}}

QPushButton {{
    background-color: #6366F1;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 9px 18px;
    font-size: 14px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: #4F46E5;
}}
QPushButton#primaryBtn {{
    background-color: #6366F1;
    color: #FFFFFF;
}}
QPushButton#primaryBtn:hover {{
    background-color: #4F46E5;
}}
QPushButton#outlineBtn {{
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    color: #334155;
}}
QPushButton#outlineBtn:hover {{
    background-color: #F1F5F9;
    border-color: #94A3B8;
    color: #0F172A;
}}

QPushButton#toggleModeBtn {{
    background-color: #EEF2FF;
    color: #4338CA;
    border: 1px solid #C7D2FE;
    border-radius: 8px;
    padding: 6px 14px;
    font-weight: bold;
    font-size: 14px;
}}
QPushButton#toggleModeBtn:hover {{
    background-color: #E0E7FF;
}}

QFrame#nettCard {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4338CA, stop:1 #0D9488);
    border-radius: 14px;
}}
QFrame#updateBanner {{
    background-color: #EEF2FF;
    border: 1px solid #C7D2FE;
    border-radius: 10px;
}}
QLabel#nettTitle {{
    font-size: 13px;
    font-weight: bold;
    color: #E0E7FF;
    letter-spacing: 1px;
}}
QLabel#nettValue {{
    font-size: 34px;
    font-weight: 800;
    color: #FFFFFF;
}}

QTableWidget {{
    background-color: #FFFFFF;
    color: #1E293B;
    gridline-color: #F1F5F9;
    font-size: 14px;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
}}
QTableWidget::item:selected {{
    background-color: #EEF2FF;
    color: #4338CA;
}}
QHeaderView::section {{
    background-color: #F8FAFC;
    color: #475569;
    font-weight: bold;
    font-size: 13px;
    padding: 10px;
    border: none;
    border-bottom: 1px solid #E2E8F0;
}}

QTabWidget::pane {{
    border: 1px solid #E2E8F0;
    background-color: #FFFFFF;
    border-radius: 10px;
    padding: 8px;
}}
QTabBar::tab {{
    background-color: #F1F5F9;
    color: #64748B;
    border: 1px solid #E2E8F0;
    padding: 6px 12px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: bold;
}}
QTabBar::tab:selected {{
    background-color: #6366F1;
    color: #FFFFFF;
    border-color: #6366F1;
}}
"""

SOFT_PAPER_DARK_QSS = """
QMainWindow, QDialog {{
    background-color: #0F172A;
    color: #F8FAFC;
    font-family: 'Segoe UI', Arial, sans-serif;
}}
QWidget {{
    font-family: 'Segoe UI', Arial, sans-serif;
    color: #F8FAFC;
}}

QScrollArea, QScrollArea > QWidget, QAbstractScrollArea::viewport, #inputScroll, #inputWidget {{
    background-color: transparent;
    border: none;
}}

QFrame#leftCard, QFrame#rightCard {{
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 14px;
}}

QLabel {{
    font-size: 14px;
    font-weight: 500;
    color: #F8FAFC;
    background: transparent;
}}
QLabel#appTitle {{
    font-size: 20px;
    font-weight: bold;
    color: #818CF8;
}}
QLabel#sectionTitle {{
    font-size: 22px;
    font-weight: bold;
    color: #818CF8;
    letter-spacing: 0.3px;
}}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 7px 12px;
    color: #F8FAFC;
    font-size: 14px;
    selection-background-color: #818CF8;
    selection-color: #0F172A;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1.5px solid #818CF8;
    background-color: #0F172A;
}}

QComboBox QAbstractItemView {{
    background-color: #0F172A;
    color: #F8FAFC;
    border: 1px solid #334155;
    selection-background-color: #312E81;
    selection-color: #FFFFFF;
    padding: 4px;
}}

QCheckBox, QRadioButton {{
    color: #F8FAFC;
    background: transparent;
    font-size: 14px;
    font-weight: 500;
    spacing: 8px;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1.5px solid #475569;
    background-color: #0F172A;
}}
QCheckBox::indicator {{
    border-radius: 4px;
}}
QRadioButton::indicator {{
    border-radius: 9px;
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: #818CF8;
}}
QCheckBox::indicator:checked {{
    background-color: #0F172A;
    border: 1.5px solid #818CF8;
    image: url('{check_dark_url}');
}}
QRadioButton::indicator:checked {{
    background-color: #0F172A;
    border: 1.5px solid #818CF8;
    image: url('{radio_dark_url}');
}}

QGroupBox {{
    border: 1px solid #334155;
    border-radius: 12px;
    margin-top: 12px;
    padding-top: 14px;
    font-weight: bold;
    font-size: 14px;
    color: #94A3B8;
    background-color: #1E293B;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 2px 10px;
    background-color: #312E81;
    border: 1px solid #4338CA;
    border-radius: 10px;
    color: #C7D2FE;
    font-weight: bold;
}}

QPushButton {{
    background-color: #818CF8;
    color: #0F172A;
    border: none;
    border-radius: 8px;
    padding: 9px 18px;
    font-size: 14px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: #A5B4FC;
}}
QPushButton#primaryBtn {{
    background-color: #818CF8;
    color: #0F172A;
}}
QPushButton#primaryBtn:hover {{
    background-color: #A5B4FC;
}}
QPushButton#outlineBtn {{
    background-color: #1E293B;
    border: 1px solid #334155;
    color: #94A3B8;
}}
QPushButton#outlineBtn:hover {{
    background-color: #334155;
    color: #F8FAFC;
}}

QPushButton#toggleModeBtn {{
    background-color: #312E81;
    color: #C7D2FE;
    border: 1px solid #4338CA;
    border-radius: 8px;
    padding: 6px 14px;
    font-weight: bold;
    font-size: 14px;
}}
QPushButton#toggleModeBtn:hover {{
    background-color: #3730A3;
}}

QFrame#nettCard {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #312E81, stop:1 #115E59);
    border-radius: 14px;
}}
QFrame#updateBanner {{
    background-color: #312E81;
    border: 1px solid #4338CA;
    border-radius: 10px;
}}
QLabel#nettTitle {{
    font-size: 13px;
    font-weight: bold;
    color: #C7D2FE;
    letter-spacing: 1px;
}}
QLabel#nettValue {{
    font-size: 34px;
    font-weight: 800;
    color: #FFFFFF;
}}

QTableWidget {{
    background-color: #1E293B;
    color: #F8FAFC;
    gridline-color: #334155;
    font-size: 14px;
    border: 1px solid #334155;
    border-radius: 10px;
}}
QTableWidget::item:selected {{
    background-color: #312E81;
    color: #FFFFFF;
}}
QHeaderView::section {{
    background-color: #0F172A;
    color: #94A3B8;
    font-weight: bold;
    font-size: 13px;
    padding: 10px;
    border: none;
    border-bottom: 1px solid #334155;
}}

QTabWidget::pane {{
    border: 1px solid #334155;
    background-color: #1E293B;
    border-radius: 10px;
    padding: 8px;
}}
QTabBar::tab {{
    background-color: #0F172A;
    color: #94A3B8;
    border: 1px solid #334155;
    padding: 6px 12px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: bold;
}}
QTabBar::tab:selected {{
    background-color: #818CF8;
    color: #0F172A;
    border-color: #818CF8;
}}
"""

def get_theme_qss(mode="dark"):
    """
    Retrieves the QSS string for Soft Material Paper theme based on mode.
    """
    if mode.lower() == "light":
        return SOFT_PAPER_LIGHT_QSS.format(
            check_light_url=CHECK_LIGHT_URL,
            radio_light_url=RADIO_LIGHT_URL
        )
    return SOFT_PAPER_DARK_QSS.format(
        check_dark_url=CHECK_DARK_URL,
        radio_dark_url=RADIO_DARK_URL
    )

def apply_theme(target, mode="dark"):
    """
    Applies the Soft Material Paper theme to the given PySide6 target widget or application.
    """
    qss = get_theme_qss(mode)
    try:
        target.setStyleSheet(qss)
    except Exception as e:
        logging.error(f"Failed to apply theme: {e}")
