"""Orders module widget."""
from datetime import datetime, date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QLineEdit,
    QDoubleSpinBox, QComboBox, QMessageBox, QAbstractItemView,
    QDateEdit, QTextEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from database.session import get_db
from database.models import Order, Client, OrderItem, Employee
from config.settings import ORDER_STATUSES


class ClientSelectDialog(QDialog):
    """Select or create client."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.client_id = None
        self.setWindowTitle("Клиент")
        self.setMinimumWidth(400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("ФИО клиента")
        layout.addWidget(self.name_edit)

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("Телефон")
        layout.addWidget(self.phone_edit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept_dialog)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

    def accept_dialog(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите ФИО клиента")
            return
        self.accept()

    def get_client_data(self):
        return {
            "full_name": self.name_edit.text().strip(),
            "phone": self.phone_edit.text().strip() or None,
        }


class OrderEditDialog(QDialog):
    """Add/Edit order dialog."""

    def __init__(self, parent=None, order: Order = None):
        super().__init__(parent)
        self.order = order
        self.client_id = None
        self.setWindowTitle("Редактировать заказ" if order else "Новый заказ")
        self.setMinimumSize(500, 400)
        self.setup_ui()
        if order:
            self.load_data()
            if self.main_window:
                self.main_window.show_toast("Заказ сохранён")
        else:
            self.load_clients()

    def setup_ui(self):
        layout = QFormLayout(self)
        self.client_combo = QComboBox()
        self.client_combo.setMinimumWidth(250)
        self.client_combo.currentIndexChanged.connect(self.on_client_selected)
        self.client_btn = QPushButton("+ Новый клиент")
        self.client_btn.clicked.connect(self.add_new_client)
        client_layout = QHBoxLayout()
        client_layout.addWidget(self.client_combo)
        client_layout.addWidget(self.client_btn)
        layout.addRow("Клиент:", client_layout)

        self.status_combo = QComboBox()
        for val, label in ORDER_STATUSES.items():
            self.status_combo.addItem(label, val)
        layout.addRow("Статус:", self.status_combo)

        self.deadline_edit = QDateEdit()
        self.deadline_edit.setCalendarPopup(True)
        layout.addRow("Срок:", self.deadline_edit)

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 10000000)
        self.amount_spin.setSuffix(" ₽")
        layout.addRow("Сумма:", self.amount_spin)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Описание заказа")
        self.desc_edit.setMaximumHeight(100)
        layout.addRow("Описание:", self.desc_edit)

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

    def load_clients(self):
        self.client_combo.clear()
        self.client_combo.addItem("— Выберите клиента —", None)
        with get_db() as db:
            for c in db.query(Client).order_by(Client.full_name).all():
                self.client_combo.addItem(f"{c.full_name} ({c.phone or '-'})", c.id)

    def on_client_selected(self):
        cid = self.client_combo.currentData()
        if cid:
            self.client_id = cid

    def load_data(self):
        o = self.order
        self.client_id = o.client_id
        self.load_clients()
        idx = self.client_combo.findData(o.client_id)
        if idx >= 0:
            self.client_combo.setCurrentIndex(idx)
        idx = self.status_combo.findData(o.status)
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)
        self.amount_spin.setValue(o.total_amount or 0)
        self.desc_edit.setPlainText(o.description or "")
        if o.deadline:
            self.deadline_edit.setDate(o.deadline)
        else:
            self.deadline_edit.setDate(date.today())

    def add_new_client(self):
        dlg = ClientSelectDialog(self)
        if dlg.exec() == dlg.Accepted:
            with get_db() as db:
                client = Client(**dlg.get_client_data())
                db.add(client)
                db.commit()
                self.client_id = client.id
                self.load_clients()
                idx = self.client_combo.findData(client.id)
                if idx >= 0:
                    self.client_combo.setCurrentIndex(idx)

    def save(self):
        if not self.client_id:
            QMessageBox.warning(self, "Ошибка", "Выберите клиента")
            return
        self.accept()

    def get_data(self):
        return {
            "client_id": self.client_id,
            "status": self.status_combo.currentData(),
            "total_amount": self.amount_spin.value(),
            "description": self.desc_edit.toPlainText().strip() or None,
            "deadline": self.deadline_edit.date().toPython(),
        }


class OrdersWidget(QWidget):
    """Orders list and management."""

    def __init__(self, main_window=None):
        super().__init__(main_window)
        self.main_window = main_window
        self._orders_data = []
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+ Новый заказ")
        add_btn.clicked.connect(self.add_order)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по клиенту, №, сумме...")
        self.search_edit.textChanged.connect(self.apply_filter)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(self.search_edit)
        btn_layout.addStretch()
        refresh_btn = QPushButton("Обновить")
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self.load_data)
        btn_layout.addWidget(refresh_btn)
        layout.addLayout(btn_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["№", "Клиент", "Статус", "Сумма", "Срок", "Дата"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.doubleClicked.connect(self.edit_order)
        layout.addWidget(self.table)

        edit_btn = QPushButton("Редактировать")
        edit_btn.clicked.connect(self.edit_order)
        layout.addWidget(edit_btn)

    def load_data(self):
        with get_db() as db:
            orders = db.query(Order).order_by(Order.created_at.desc()).all()
            self._orders_data = []
            for o in orders:
                client = db.query(Client).get(o.client_id)
                client_name = client.full_name if client else "-"
                row = {
                    "id": o.id, "client_name": client_name, "status": o.status,
                    "amount": o.total_amount or 0, "deadline": o.deadline, "created": o.created_at
                }
                self._orders_data.append(row)
            self.apply_filter()

    def apply_filter(self):
        q = self.search_edit.text().strip().lower() if hasattr(self, "search_edit") else ""
        filtered = self._orders_data
        if q:
            filtered = [r for r in self._orders_data
                        if q in str(r["id"]).lower() or q in (r["client_name"] or "").lower()
                        or q in str(r["amount"]).lower() or q in (ORDER_STATUSES.get(r["status"], r["status"]) or "").lower()]
        self.table.setRowCount(len(filtered))
        for i, row in enumerate(filtered):
            self.table.setItem(i, 0, QTableWidgetItem(str(row["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(row["client_name"]))
            self.table.setItem(i, 2, QTableWidgetItem(ORDER_STATUSES.get(row["status"], row["status"])))
            self.table.setItem(i, 3, QTableWidgetItem(f"{row['amount']:,.0f} ₽"))
            self.table.setItem(i, 4, QTableWidgetItem(row["deadline"].strftime("%d.%m.%Y") if row["deadline"] else "-"))
            self.table.setItem(i, 5, QTableWidgetItem(row["created"].strftime("%d.%m.%Y") if row["created"] else "-"))
            self.table.item(i, 0).setData(Qt.UserRole, row["id"])

    def add_order(self):
        dlg = OrderEditDialog(self)
        if dlg.exec() == dlg.Accepted:
            with get_db() as db:
                order = Order(**dlg.get_data())
                db.add(order)
                db.commit()
            self.load_data()
            if self.main_window:
                self.main_window.show_toast("Заказ сохранён")

    def edit_order(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Информация", "Выберите заказ")
            return
        order_id = self.table.item(row, 0).data(Qt.UserRole)
        with get_db() as db:
            order = db.query(Order).get(order_id)
            if not order:
                return
            dlg = OrderEditDialog(self, order)
            if dlg.exec() == dlg.Accepted:
                data = dlg.get_data()
                for k, v in data.items():
                    setattr(order, k, v)
                if order.status == "ready" and not order.completed_at:
                    order.completed_at = datetime.utcnow()
                db.commit()
                self.load_data()
                if self.main_window:
                    self.main_window.show_toast("Заказ обновлён")
