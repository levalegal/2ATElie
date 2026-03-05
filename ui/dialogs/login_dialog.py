"""Login dialog."""
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QFont

from database.session import get_db
from modules.auth.service import authenticate, get_user_role


class LoginDialog(QDialog):
    """Login dialog with remember username."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user = None
        self.role = None
        self.setup_ui()
        self._load_theme()
        self._load_saved_username()

    def _load_theme(self):
        theme = QSettings("Atelier", "2ATElie").value("theme", "dark")
        base = Path(__file__).parent.parent
        theme_file = base / "styles" / f"theme_{theme}.qss"
        if theme_file.exists():
            with open(theme_file, encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def setup_ui(self):
        self.setWindowTitle("Вход в систему — Ателье")
        self.setMinimumSize(480, 420)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(48, 48, 48, 48)

        # Title
        title = QLabel("Ателье")
        title.setObjectName("login_title")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(32)
        title_font.setWeight(QFont.Bold)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = QLabel("Учёт заказов, зарплат и затрат")
        subtitle.setObjectName("login_subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        layout.addSpacing(24)

        # Form frame
        frame = QFrame()
        frame.setObjectName("card")
        form_layout = QVBoxLayout(frame)
        form_layout.setSpacing(12)

        login_label = QLabel("Логин")
        form_layout.addWidget(login_label)
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Введите логин (admin, manager, designer...)")
        self.username_edit.setMinimumHeight(44)
        form_layout.addWidget(self.username_edit)
        form_layout.addSpacing(8)

        pass_label = QLabel("Пароль")
        form_layout.addWidget(pass_label)
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Введите пароль")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setMinimumHeight(44)
        self.password_edit.returnPressed.connect(self.do_login)
        form_layout.addWidget(self.password_edit)
        form_layout.addSpacing(12)

        self.remember_check = QCheckBox("Запомнить логин")
        self.remember_check.setChecked(True)
        form_layout.addWidget(self.remember_check)

        hint = QLabel("Тестовые: admin, manager, designer, constructor, cutter, tailor — пароль: admin123")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray; font-size: 11px;")
        form_layout.addWidget(hint)

        layout.addWidget(frame)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        login_btn = QPushButton("Войти")
        login_btn.setMinimumWidth(140)
        login_btn.setMinimumHeight(40)
        login_btn.clicked.connect(self.do_login)
        btn_layout.addWidget(login_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def do_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Введите логин и пароль")
            return

        with get_db() as db:
            user = authenticate(db, username, password)
            if not user:
                QMessageBox.warning(self, "Ошибка", "Неверный логин или пароль")
                return
            role = get_user_role(db, user)
            if not role:
                QMessageBox.warning(self, "Ошибка", "Роль пользователя не найдена")
                return
            self.user = user
            self.role = role

        if self.remember_check.isChecked():
            QSettings("Atelier", "Login").setValue("username", username)
        else:
            QSettings("Atelier", "Login").remove("username")
        self.accept()

    def _load_saved_username(self):
        saved = QSettings("Atelier", "Login").value("username", "")
        if saved:
            self.username_edit.setText(saved)
            self.remember_check.setChecked(True)

    def get_user(self):
        return self.user

    def get_role(self):
        return self.role
