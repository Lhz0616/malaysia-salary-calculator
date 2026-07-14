import sys

from PySide6.QtWidgets import QApplication
from  ui.main_window import MainWindow

def main():
    # Enable high-DPI scaling if available on the system
    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("Malaysian Payroll Engine")
    app.setOrganizationName("Demo Corp")

    # Create and display the main window
    window = MainWindow()
    window.showMaximized()

    # Run the application event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
