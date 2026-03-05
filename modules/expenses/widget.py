"""Expenses module widget."""
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QLineEdit,
    QDoubleSpinBox, QComboBox, QMessageBox, QAbstractItemView,
    QDateEdit, QGroupBox
)
from PySide6.QtCore import Qt

from database.session import get_db
from database.models import Expense, ExpenseCategory


class ExpenseEditDialog(QDialog):
    """Add/Edit expense dialog."""

    def __init__(self, parent=None, expense: Expense = None):
        super().__init__(parent)
        self.expense = expense
        self.setWindowTitle("Редактировать расход" if expense else "Добавить расход")
        self.setMinimumWidth(400)
        self.setup_ui()
        if expense:
            self.load_data()

    def setup_ui(self):
        layout = QFormLayout(self)
        self.category_combo = QComboBox()
        with get_db() as db:
            for cat in db.query(ExpenseCategory).order_by(ExpenseCategory.name).all():
                self.category_combo.addItem(cat.name, cat.id)
        layout.addRow("Категория:", self.category_combo)

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 100000000)
        self.amount_spin.setSuffix(" ₽")
        layout.addRow("Сумма:", self.amount_spin)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(date.today())
        layout.addRow("Дата:", self.date_edit)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Описание")
        layout.addRow("Описание:", self.desc_edit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addRow(btn_layout)

    def load_data(self):
        e = self.expense
        idx = self.category_combo.findData(e.category_id)
        if idx >= 0:
            self.category_combo.setCurrentIndex(idx)
        self.amount_spin.setValue(e.amount or 0)
        self.date_edit.setDate(e.date or date.today())
        self.desc_edit.setText(e.description or "")

    def get_data(self):
        return {
            "category_id": self.category_combo.currentData(),
            "amount": self.amount_spin.value(),
            "date": self.date_edit.date().toPython(),
            "description": self.desc_edit.text().strip() or None,
        }


class ExpensesWidget(QWidget):
    """Expenses list and management."""

    def __init__(self, main_window=None):
        super().__init__(main_window)
        self.main_window = main_window
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+ Добавить расход")
        add_btn.clicked.connect(self.add_expense)
        btn_layout.addWidget(add_btn)
        btn_layout.addStretch()
        refresh_btn = QPushButton("Обновить")
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self.load_data)
        btn_layout.addWidget(refresh_btn)
        layout.addLayout(btn_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Дата", "Категория", "Сумма", "Описание", ""])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.doubleClicked.connect(self.edit_expense)
        layout.addWidget(self.table)

        edit_btn = QPushButton("Редактировать")
        edit_btn.clicked.connect(self.edit_expense)
        layout.addWidget(edit_btn)

    def load_data(self):
        with get_db() as db:
            expenses = db.query(Expense).order_by(Expense.date.desc()).all()
            self.table.setRowCount(len(expenses))
            for i, e in enumerate(expenses):
                cat = db.query(ExpenseCategory).get(e.category_id)
                cat_name = cat.name if cat else "-"
                self.table.setItem(i, 0, QTableWidgetItem(e.date.strftime("%d.%m.%Y") if e.date else "-"))
                self.table.setItem(i, 1, QTableWidgetItem(cat_name))
                self.table.setItem(i, 2, QTableWidgetItem(f"{e.amount or 0:,.0f} ₽"))
                self.table.setItem(i, 3, QTableWidgetItem(e.description or ""))
                self.table.item(i, 0).setData(Qt.UserRole, e.id)

    def add_expense(self):
        dlg = ExpenseEditDialog(self)
        if dlg.exec() == dlg.Accepted:
            with get_db() as db:
                exp = Expense(**dlg.get_data())
                db.add(exp)
                db.commit()
            self.load_data()

    def edit_expense(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Информация", "Выберите расход")
            return
        exp_id = self.table.item(row, 0).data(Qt.UserRole)
        with get_db() as db:
            exp = db.query(Expense).get(exp_id)
            if not exp:
                return
            dlg = ExpenseEditDialog(self, exp)
            if dlg.exec() == dlg.Accepted:
                data = dlg.get_data()
                for k, v in data.items():
                    setattr(exp, k, v)
                db.commit()
                self.load_data()
