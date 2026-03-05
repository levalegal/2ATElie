"""Employees module widget."""
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QLineEdit,
    QDoubleSpinBox, QComboBox, QMessageBox, QAbstractItemView, QFileDialog
)
from PySide6.QtCore import Qt

from database.session import get_db
from database.models import Employee
from config.settings import ROLES
from utils.export import export_employees_to_excel


POSITIONS = [
    ("designer", "Дизайнер"),
    ("constructor", "Модельер-конструктор"),
    ("cutter", "Закройщик"),
    ("tailor", "Портной"),
]


class EmployeeEditDialog(QDialog):
    """Add/Edit employee dialog."""

    def __init__(self, parent=None, employee: Employee = None):
        super().__init__(parent)
        self.employee = employee
        self.setWindowTitle("Редактировать сотрудника" if employee else "Добавить сотрудника")
        self.setMinimumWidth(400)
        self.setup_ui()
        if employee:
            self.load_data()

    def setup_ui(self):
        layout = QFormLayout(self)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("ФИО")
        layout.addRow("ФИО:", self.name_edit)

        self.position_combo = QComboBox()
        for val, label in POSITIONS:
            self.position_combo.addItem(label, val)
        layout.addRow("Должность:", self.position_combo)

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("+7 ...")
        layout.addRow("Телефон:", self.phone_edit)

        self.base_salary = QDoubleSpinBox()
        self.base_salary.setRange(0, 1000000)
        self.base_salary.setSuffix(" ₽")
        layout.addRow("Базовая ставка:", self.base_salary)

        self.order_percent = QDoubleSpinBox()
        self.order_percent.setRange(0, 100)
        self.order_percent.setSuffix(" %")
        layout.addRow("% от заказа:", self.order_percent)

        self.hourly_rate = QDoubleSpinBox()
        self.hourly_rate.setRange(0, 10000)
        self.hourly_rate.setSuffix(" ₽/ч")
        layout.addRow("Почасовая ставка:", self.hourly_rate)

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
        e = self.employee
        self.name_edit.setText(e.full_name)
        idx = self.position_combo.findData(e.position)
        if idx >= 0:
            self.position_combo.setCurrentIndex(idx)
        self.phone_edit.setText(e.phone or "")
        self.base_salary.setValue(e.base_salary or 0)
        self.order_percent.setValue(e.order_percent or 0)
        self.hourly_rate.setValue(e.hourly_rate or 0)

    def save(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите ФИО")
            return
        self.accept()

    def get_data(self):
        return {
            "full_name": self.name_edit.text().strip(),
            "position": self.position_combo.currentData(),
            "phone": self.phone_edit.text().strip() or None,
            "base_salary": self.base_salary.value(),
            "order_percent": self.order_percent.value(),
            "hourly_rate": self.hourly_rate.value(),
        }


class EmployeesWidget(QWidget):
    """Employees list and management."""

    def __init__(self, main_window=None):
        super().__init__(main_window)
        self.main_window = main_window
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+ Добавить сотрудника")
        add_btn.clicked.connect(self.add_employee)
        export_btn = QPushButton("Экспорт в Excel")
        export_btn.setObjectName("secondary")
        export_btn.clicked.connect(self.export_report)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(export_btn)
        btn_layout.addStretch()
        refresh_btn = QPushButton("Обновить")
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self.load_data)
        btn_layout.addWidget(refresh_btn)
        layout.addLayout(btn_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ФИО", "Должность", "Телефон", "Ставка", "% от заказа", "₽/ч"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit_employee)
        layout.addWidget(self.table)

        edit_btn = QPushButton("Редактировать")
        edit_btn.clicked.connect(self.edit_employee)
        layout.addWidget(edit_btn)

    def load_data(self):
        with get_db() as db:
            employees = db.query(Employee).order_by(Employee.full_name).all()
            self.table.setRowCount(len(employees))
            pos_map = dict(POSITIONS)
            for i, emp in enumerate(employees):
                self.table.setItem(i, 0, QTableWidgetItem(emp.full_name))
                self.table.setItem(i, 1, QTableWidgetItem(pos_map.get(emp.position, emp.position)))
                self.table.setItem(i, 2, QTableWidgetItem(emp.phone or ""))
                self.table.setItem(i, 3, QTableWidgetItem(f"{emp.base_salary or 0:,.0f}"))
                self.table.setItem(i, 4, QTableWidgetItem(f"{emp.order_percent or 0}%"))
                self.table.setItem(i, 5, QTableWidgetItem(f"{emp.hourly_rate or 0:,.0f}"))
                self.table.item(i, 0).setData(Qt.UserRole, emp.id)

    def add_employee(self):
        dlg = EmployeeEditDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            with get_db() as db:
                emp = Employee(**dlg.get_data())
                db.add(emp)
                db.commit()
            self.load_data()

    def edit_employee(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Информация", "Выберите сотрудника")
            return
        emp_id = self.table.item(row, 0).data(Qt.UserRole)
        with get_db() as db:
            emp = db.query(Employee).get(emp_id)
            if not emp:
                return
            dlg = EmployeeEditDialog(self, emp)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                data = dlg.get_data()
                for k, v in data.items():
                    setattr(emp, k, v)
                db.commit()
                self.load_data()

    def export_report(self):
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт", "", "Excel (*.xlsx)")
        if not path:
            return
        pos_map = dict(POSITIONS)
        records = []
        with get_db() as db:
            for emp in db.query(Employee).order_by(Employee.full_name).all():
                records.append({
                    "name": emp.full_name,
                    "position": pos_map.get(emp.position, emp.position),
                    "phone": emp.phone or "",
                    "base_salary": emp.base_salary or 0,
                    "order_percent": emp.order_percent or 0,
                    "hourly_rate": emp.hourly_rate or 0,
                })
        export_employees_to_excel(records, path)
        QMessageBox.information(self, "Готово", "Сохранено")
