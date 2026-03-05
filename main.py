"""Atelier management application - entry point."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from database.session import init_db
from database.init_data import run_init
from ui.dialogs.login_dialog import LoginDialog
from ui.main_window import MainWindow


def main():
    # Initialize database
    run_init()

    app = QApplication(sys.argv)
    app.setApplicationName("Ателье")
    app.setOrganizationName("Atelier")

    # Default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # High DPI
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Login
    login = LoginDialog()
    if login.exec() != login.Accepted:
        return 0

    user = login.get_user()
    role = login.get_role()

    # Main window
    window = MainWindow(user, role)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
