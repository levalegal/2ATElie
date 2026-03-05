"""Atelier management application - entry point."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QBrush

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

    # App icon
    icon_path = Path(__file__).parent / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    else:
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QBrush(QColor("#8b3a3a")))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(4, 4, 56, 56, 12, 12)
        painter.end()
        app.setWindowIcon(QIcon(pixmap))

    # Default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # High DPI
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Login
    login = LoginDialog()
    if login.exec() != QDialog.DialogCode.Accepted:
        return 0

    user = login.get_user()
    role = login.get_role()

    # Main window
    window = MainWindow(user, role)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
