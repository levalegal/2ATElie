"""Admin panel - users and roles management."""
import bcrypt
import shutil
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QLineEdit,
    QComboBox, QMessageBox, QAbstractItemView, QGroupBox, QFileDialog, QLabel
)
from PySide6.QtCore import Qt

from database.session import get_db
from database.models import User, Role, Employee
from database.test_data import load_test_data as do_load_test_data
from config.settings import DB_PATH, DATA_DIR


class UserEditDialog(QDialog):
    """Add/Edit user dialog."""

    def __init__(self, parent=None, user: User = None):
        super().__init__(parent)
        self.user = user
        self.setWindowTitle("Редактировать пользователя" if user else "Добавить пользователя")
        self.setMinimumWidth(400)
        self.setup_ui()
        if user:
            self.load_data()

    def setup_ui(self):
        layout = QFormLayout(self)
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Логин")
        self.username_edit.setEnabled(self.user is None)  # Can't change username when editing
        layout.addRow("Логин:", self.username_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Новый пароль (оставьте пустым для сохранения)" if self.user else "Пароль")
        self.password_edit.setEchoMode(QLineEdit.Password)
        layout.addRow("Пароль:", self.password_edit)

        self.role_combo = QComboBox()
        with get_db() as db:
            for r in db.query(Role).order_by(Role.name).all():
                self.role_combo.addItem(r.display_name, r.id)
        layout.addRow("Роль:", self.role_combo)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addRow(btn_layout)

    def load_data(self):
        u = self.user
        self.username_edit.setText(u.username)
        idx = self.role_combo.findData(u.role_id)
        if idx >= 0:
            self.role_combo.setCurrentIndex(idx)

    def save(self):
        if not self.username_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите логин")
            return
        if not self.user and not self.password_edit.text():
            QMessageBox.warning(self, "Ошибка", "Введите пароль")
            return
        self.accept()

    def get_data(self):
        data = {
            "username": self.username_edit.text().strip(),
            "role_id": self.role_combo.currentData(),
        }
        if self.password_edit.text():
            data["password_hash"] = bcrypt.hashpw(
                self.password_edit.text().encode(),
                bcrypt.gensalt()
            ).decode()
        return data


class AdminWidget(QWidget):
    """Admin panel - users, backup."""

    def __init__(self, main_window=None):
        super().__init__(main_window)
        self.main_window = main_window
        self.setup_ui()
        self.load_users()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        # Users
        users_group = QGroupBox("Пользователи")
        users_layout = QVBoxLayout(users_group)
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+ Добавить пользователя")
        add_btn.clicked.connect(self.add_user)
        btn_layout.addWidget(add_btn)
        refresh_btn = QPushButton("Обновить")
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self.load_users)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addStretch()
        users_layout.addLayout(btn_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Логин", "Роль", "Активен", ""])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.doubleClicked.connect(self.edit_user)
        users_layout.addWidget(self.table)
        layout.addWidget(users_group)

        edit_btn = QPushButton("Редактировать")
        edit_btn.clicked.connect(self.edit_user)
        layout.addWidget(edit_btn)

        # Test data
        test_group = QGroupBox("Тестовые данные")
        test_layout = QVBoxLayout(test_group)
        test_btn = QPushButton("Загрузить тестовые данные")
        test_btn.setStyleSheet("background-color: #2d5a27;")  # Green accent
        test_btn.clicked.connect(self.load_test_data)
        test_layout.addWidget(QLabel("Загружает сотрудников, клиентов, заказы, материалы и расходы для демонстрации."))
        test_layout.addWidget(test_btn)
        layout.addWidget(test_group)

        # Backup
        backup_group = QGroupBox("Резервное копирование")
        backup_layout = QVBoxLayout(backup_group)
        backup_btn = QPushButton("Создать резервную копию БД")
        backup_btn.clicked.connect(self.backup_db)
        backup_layout.addWidget(backup_btn)
        layout.addWidget(backup_group)

    def load_users(self):
        with get_db() as db:
            users = db.query(User).order_by(User.username).all()
            self.table.setRowCount(len(users))
            for i, u in enumerate(users):
                role = db.query(Role).get(u.role_id)
                role_name = role.display_name if role else "-"
                self.table.setItem(i, 0, QTableWidgetItem(u.username))
                self.table.setItem(i, 1, QTableWidgetItem(role_name))
                self.table.setItem(i, 2, QTableWidgetItem("Да" if u.is_active else "Нет"))
                self.table.item(i, 0).setData(Qt.UserRole, u.id)

    def add_user(self):
        dlg = UserEditDialog(self)
        if dlg.exec() == dlg.Accepted:
            data = dlg.get_data()
            if "password_hash" not in data:
                return
            with get_db() as db:
                if db.query(User).filter(User.username == data["username"]).first():
                    QMessageBox.warning(self, "Ошибка", "Пользователь с таким логином уже существует")
                    return
                user = User(
                    username=data["username"],
                    password_hash=data["password_hash"],
                    role_id=data["role_id"],
                )
                db.add(user)
                db.commit()
            self.load_users()

    def edit_user(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Информация", "Выберите пользователя")
            return
        user_id = self.table.item(row, 0).data(Qt.UserRole)
        with get_db() as db:
            user = db.query(User).get(user_id)
            if not user:
                return
            dlg = UserEditDialog(self, user)
            if dlg.exec() == dlg.Accepted:
                data = dlg.get_data()
                user.role_id = data["role_id"]
                if "password_hash" in data:
                    user.password_hash = data["password_hash"]
                db.commit()
                self.load_users()

    def load_test_data(self):
        reply = QMessageBox.question(
            self,
            "Тестовые данные",
            "Загрузить тестовые данные? Существующие данные (кроме admin) будут удалены.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                do_load_test_data()
                QMessageBox.information(self, "Готово", "Тестовые данные загружены.")
                # Refresh all pages that might show data
                if self.main_window and hasattr(self.main_window, "pages"):
                    for name, page in self.main_window.pages.items():
                        if hasattr(page, "load_data"):
                            page.load_data()
                        if hasattr(page, "refresh"):
                            page.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def backup_db(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить резервную копию",
            str(Path.home()),
            "SQLite DB (*.db);;All Files (*)"
        )
        if path:
            try:
                shutil.copy2(DB_PATH, path)
                QMessageBox.information(self, "Готово", f"Резервная копия сохранена: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))
