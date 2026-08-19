import ctypes
import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from core.config_loader import get_resource_path
from ui.main_window import MainWindow


def main():
    # Set Windows AppUserModelID so Taskbar displays the custom icon instead of python.exe default icon
    if sys.platform == "win32":
        try:
            myappid = "malaysia.payroll.calculator.app.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    # Enable high-DPI scaling if available on the system
    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("Malaysian Payroll Engine")
    app.setOrganizationName("Demo Corp")

    # Set application window icon
    icon_path = get_resource_path("icon/app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Create and display the main window
    window = MainWindow()
    window.showMaximized()

    # Run the application event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
