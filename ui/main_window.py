"""Main application window."""
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QPushButton, QLabel, QFrame, QScrollArea, QSizePolicy, QStatusBar
)
from PySide6.QtCore import Qt, QSettings, QPoint
from PySide6.QtGui import QFont, QAction, QKeySequence, QShortcut
from database.models import User, Role
from ui.widgets.toast import Toast
from config.settings import ROLES
from modules.orders.widget import OrdersWidget
from modules.employees.widget import EmployeesWidget
from modules.materials.widget import MaterialsWidget
from modules.dashboard.widget import DashboardWidget
from modules.salary.widget import SalaryWidget
from modules.expenses.widget import ExpensesWidget
from modules.admin.widget import AdminWidget


class MainWindow(QMainWindow):
    """Main application window with sidebar navigation."""

    def __init__(self, user: User, role: Role):
        super().__init__()
        self.user = user
        self.role = role
        self.settings = QSettings("Atelier", "2ATElie")
        self.stacked = QStackedWidget()
        self.pages = {}
        self.setup_ui()
        self.load_theme()

    def setup_ui(self):
        self.setWindowTitle("Ателье — Система учёта")
        self.setMinimumSize(1200, 700)
        self.resize(1400, 800)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = self.create_sidebar()
        sidebar.setObjectName("sidebar")
        main_layout.addWidget(sidebar)

        # Content area
        content = QFrame()
        content.setObjectName("card")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.addWidget(self.stacked)
        main_layout.addWidget(content, 1)

        # Add pages (pass main_window for toast/refresh)
        self.pages["dashboard"] = DashboardWidget(self)
        self.stacked.addWidget(self.pages["dashboard"])
        self.pages["orders"] = OrdersWidget(self)
        self.stacked.addWidget(self.pages["orders"])
        self.pages["employees"] = EmployeesWidget(self)
        self.stacked.addWidget(self.pages["employees"])
        self.pages["materials"] = MaterialsWidget(self)
        self.pages["salary"] = SalaryWidget(self)
        self.stacked.addWidget(self.pages["salary"])
        self.pages["expenses"] = ExpensesWidget(self)
        self.stacked.addWidget(self.pages["expenses"])
        self.pages["admin"] = AdminWidget(self)
        self.stacked.addWidget(self.pages["admin"])

        # Restore last page or show dashboard (respect role access)
        last_page = self.settings.value("lastPage", "dashboard")
        if last_page in self.pages and self._can_access(last_page):
            self.navigate_to(last_page)
        else:
            self.navigate_to("dashboard")

        self.setup_shortcuts()
        self.setup_statusbar()

    def setup_statusbar(self):
        """Add status bar with shortcuts hint."""
        self.statusBar().showMessage("Ctrl+1..7 — навигация")

    def create_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(260)
        # Sidebar uses theme - no inline override
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 24, 16, 24)
        layout.setSpacing(8)

        # Logo/title
        title = QLabel("Ателье")
        title.setObjectName("sidebar_title")
        layout.addWidget(title)

        role_label = QLabel(ROLES.get(self.role.name, self.role.display_name))
        role_label.setObjectName("sidebar_role")
        layout.addWidget(role_label)
        layout.addSpacing(24)

        # Nav buttons with icons (Unicode) - filtered by role
        nav_icons = {"dashboard": "📊", "orders": "📋", "employees": "👥", "materials": "🧵",
                     "salary": "💰", "expenses": "📉", "admin": "⚙️"}
        all_nav = [
            ("dashboard", "Дашборд"),
            ("orders", "Заказы"),
            ("employees", "Сотрудники"),
            ("materials", "Материалы"),
            ("salary", "Зарплаты"),
            ("expenses", "Затраты"),
            ("admin", "Админ-панель"),
        ]
        nav_items = [(pid, lbl) for pid, lbl in all_nav if self._can_access(pid)]

        for page_id, label in nav_items:
            icon = nav_icons.get(page_id, "•")
            btn = QPushButton(f"  {icon}  {label}")
            btn.setObjectName("nav_btn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, p=page_id: self.navigate_to(p))
            layout.addWidget(btn)
            self.nav_buttons = getattr(self, "nav_buttons", {})
            self.nav_buttons[page_id] = btn

        layout.addStretch()

        # Theme toggle - show current theme
        theme = self.settings.value("theme", "dark")
        theme_btn = QPushButton(f"Тема: {'Светлая' if theme == 'light' else 'Тёмная'}")
        theme_btn.setObjectName("secondary")
        theme_btn.clicked.connect(self.toggle_theme)
        layout.addWidget(theme_btn)
        self.theme_btn = theme_btn

        return sidebar

    def add_placeholder_page(self, page_id: str, title: str, subtitle: str):
        """Add a placeholder page (will be replaced by real modules)."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(title, objectName="title"))
        layout.addWidget(QLabel(subtitle, objectName="subtitle"))
        layout.addStretch()
        self.pages[page_id] = page
        self.stacked.addWidget(page)

    def navigate_to(self, page_id: str):
        """Navigate to page."""
        if page_id in self.pages:
            self.stacked.setCurrentWidget(self.pages[page_id])
            self.settings.setValue("lastPage", page_id)
            for pid, btn in getattr(self, "nav_buttons", {}).items():
                btn.setChecked(pid == page_id)

    def setup_shortcuts(self):
        """Setup keyboard shortcuts for navigation."""
        shortcuts = [
            (Qt.CTRL | Qt.Key_1, "dashboard"),
            (Qt.CTRL | Qt.Key_2, "orders"),
            (Qt.CTRL | Qt.Key_3, "employees"),
            (Qt.CTRL | Qt.Key_4, "materials"),
            (Qt.CTRL | Qt.Key_5, "salary"),
            (Qt.CTRL | Qt.Key_6, "expenses"),
            (Qt.CTRL | Qt.Key_7, "admin"),
        ]
        for key, page_id in shortcuts:
            if page_id in self.pages and self._can_access(page_id):
                QShortcut(QKeySequence(key), self, activated=lambda p=page_id: self.navigate_to(p))

    def _can_access(self, page_id: str) -> bool:
        """Check if current role can access page."""
        if page_id == "admin":
            return self.role.name == "admin"
        if page_id in ("salary", "expenses"):
            return self.role.name in ("admin", "manager")
        if page_id == "employees":
            return self.role.name in ("admin", "manager")
        return True

    def toggle_theme(self):
        """Toggle dark/light theme."""
        current = self.settings.value("theme", "dark")
        new_theme = "light" if current == "dark" else "dark"
        self.settings.setValue("theme", new_theme)
        self.load_theme()
        self.theme_btn.setText(f"Тема: {'Светлая' if new_theme == 'light' else 'Тёмная'}")
        if "dashboard" in self.pages and hasattr(self.pages["dashboard"], "_apply_card_theme"):
            self.pages["dashboard"]._apply_card_theme()

    def load_theme(self):
        """Load QSS theme."""
        import sys
        theme = self.settings.value("theme", "dark")
        if getattr(sys, "frozen", False):
            base = Path(sys._MEIPASS) / "ui"
        else:
            base = Path(__file__).parent
        theme_file = base / "styles" / f"theme_{theme}.qss"
        if theme_file.exists():
            with open(theme_file, encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def show_toast(self, message: str, duration: int = 2500):
        """Show toast notification."""
        toast = Toast(message, self, duration)
        toast.adjustSize()
        br = self.mapToGlobal(self.rect().bottomRight())
        toast.move(br.x() - toast.width() - 20, br.y() - toast.height() - 80)
        toast.show()
