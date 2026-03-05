"""Login dialog."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QFrame, QMessageBox
)
from PySide6.QtCore import Qt
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

    def setup_ui(self):
        self.setWindowTitle("Вход в систему — Ателье")
        self.setFixedSize(400, 320)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # Title
        title = QLabel("Ателье")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setWeight(QFont.Bold)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = QLabel("Учёт заказов, зарплат и затрат")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        layout.addSpacing(20)

        # Form frame
        frame = QFrame()
        frame.setObjectName("card")
        form_layout = QVBoxLayout(frame)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Логин")
        self.username_edit.setMinimumHeight(40)
        form_layout.addWidget(self.username_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Пароль")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setMinimumHeight(40)
        self.password_edit.returnPressed.connect(self.do_login)
        form_layout.addWidget(self.password_edit)

        self.remember_check = QCheckBox("Запомнить логин")
        self.remember_check.setChecked(True)
        form_layout.addWidget(self.remember_check)

        layout.addWidget(frame)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        login_btn = QPushButton("Войти")
        login_btn.setMinimumWidth(120)
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
            self.user = user
            self.role = get_user_role(db, user)

        self.accept()

    def get_user(self):
        return self.user

    def get_role(self):
        return self.role
