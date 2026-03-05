"""Orders module widget."""
from datetime import datetime, date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QLineEdit,
    QDoubleSpinBox, QComboBox, QMessageBox, QAbstractItemView,
    QDateEdit, QTextEdit, QTabWidget, QGroupBox, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from database.session import get_db
from database.models import Order, Client, OrderItem, Employee, Material, OrderMaterial, OrderAssignment
from config.settings import ORDER_STATUSES
from utils.export import export_order_invoice

STAGES = [("design", "Дизайн"), ("construction", "Конструирование"), ("cutting", "Раскрой"), ("sewing", "Пошив")]


def _save_order_extras(db, order, dlg):
    """Save materials and assignments for order."""
    # Clear and replace assignments
    db.query(OrderAssignment).filter(OrderAssignment.order_id == order.id).delete()
    for stage_id, emp_id in dlg.get_assignments_data():
        if emp_id:
            db.add(OrderAssignment(order_id=order.id, employee_id=emp_id, stage=stage_id))
    # Clear and replace materials, deduct from stock
    for om in list(order.materials):
        mat = db.query(Material).get(om.material_id)
        if mat:
            mat.quantity = (mat.quantity or 0) + om.quantity  # Restore
        db.delete(om)
    for mat_id, qty, unit_price in dlg.get_materials_data():
        db.add(OrderMaterial(order_id=order.id, material_id=mat_id, quantity=qty, unit_price=unit_price))
        mat = db.query(Material).get(mat_id)
        if mat:
            mat.quantity = max(0, (mat.quantity or 0) - qty)


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
        self.setMinimumSize(600, 550)
        self.setup_ui()
        if order:
            self.load_data()
        else:
            self.load_clients()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        # Tab 1: Main
        main_tab = QWidget()
        form = QFormLayout(main_tab)
        self.client_combo = QComboBox()
        self.client_combo.setMinimumWidth(250)
        self.client_combo.currentIndexChanged.connect(self.on_client_selected)
        self.client_btn = QPushButton("+ Новый клиент")
        self.client_btn.clicked.connect(self.add_new_client)
        client_layout = QHBoxLayout()
        client_layout.addWidget(self.client_combo)
        client_layout.addWidget(self.client_btn)
        form.addRow("Клиент:", client_layout)

        self.status_combo = QComboBox()
        for val, label in ORDER_STATUSES.items():
            self.status_combo.addItem(label, val)
        form.addRow("Статус:", self.status_combo)

        self.deadline_edit = QDateEdit()
        self.deadline_edit.setCalendarPopup(True)
        form.addRow("Срок:", self.deadline_edit)

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 10000000)
        self.amount_spin.setSuffix(" ₽")
        form.addRow("Сумма:", self.amount_spin)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Описание заказа")
        self.desc_edit.setMaximumHeight(80)
        form.addRow("Описание:", self.desc_edit)

        tabs.addTab(main_tab, "Основное")

        # Tab 2: Materials
        mat_tab = QWidget()
        mat_layout = QVBoxLayout(mat_tab)
        self.materials_table = QTableWidget()
        self.materials_table.setColumnCount(4)
        self.materials_table.setHorizontalHeaderLabels(["Материал", "Кол-во", "Цена", ""])
        self.materials_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        mat_layout.addWidget(self.materials_table)
        add_mat_btn = QPushButton("+ Добавить материал")
        add_mat_btn.clicked.connect(self.add_material_row)
        mat_layout.addWidget(add_mat_btn)
        tabs.addTab(mat_tab, "Материалы")

        # Tab 3: Executors
        exec_tab = QWidget()
        exec_layout = QFormLayout(exec_tab)
        self.stage_combos = {}
        for stage_id, stage_name in STAGES:
            combo = QComboBox()
            combo.addItem("— Не назначен —", None)
            with get_db() as db:
                for emp in db.query(Employee).order_by(Employee.full_name).all():
                    combo.addItem(emp.full_name, emp.id)
            exec_layout.addRow(f"{stage_name}:", combo)
            self.stage_combos[stage_id] = combo
        tabs.addTab(exec_tab, "Исполнители")

        layout.addWidget(tabs)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

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

    def _remove_material_row(self):
        btn = self.sender()
        if btn:
            for r in range(self.materials_table.rowCount()):
                if self.materials_table.cellWidget(r, 3) is btn:
                    self.materials_table.removeRow(r)
                    break

    def add_material_row(self):
        row = self.materials_table.rowCount()
        self.materials_table.insertRow(row)
        combo = QComboBox()
        combo.addItem("— Выберите —", None)
        with get_db() as db:
            for m in db.query(Material).order_by(Material.name).all():
                combo.addItem(f"{m.name} ({m.unit}, {m.price_per_unit:,.0f} ₽)", m.id)
        self.materials_table.setCellWidget(row, 0, combo)
        qty = QDoubleSpinBox()
        qty.setRange(0.01, 10000)
        self.materials_table.setCellWidget(row, 1, qty)
        price = QDoubleSpinBox()
        price.setRange(0, 1000000)
        self.materials_table.setCellWidget(row, 2, price)
        del_btn = QPushButton("✕")
        del_btn.setMaximumWidth(30)
        del_btn.clicked.connect(self._remove_material_row)
        self.materials_table.setCellWidget(row, 3, del_btn)

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
        # Load materials
        self.materials_table.setRowCount(0)
        with get_db() as db:
            order = db.query(Order).get(o.id)
            if order:
                for om in order.materials:
                    mat = db.query(Material).get(om.material_id)
                    if mat:
                        self.add_material_row()
                        r = self.materials_table.rowCount() - 1
                        c0 = self.materials_table.cellWidget(r, 0)
                        if c0:
                            idx = c0.findData(om.material_id)
                            if idx >= 0:
                                c0.setCurrentIndex(idx)
                        c1 = self.materials_table.cellWidget(r, 1)
                        if c1:
                            c1.setValue(om.quantity)
                        c2 = self.materials_table.cellWidget(r, 2)
                        if c2:
                            c2.setValue(om.unit_price or mat.price_per_unit)
                for a in order.assignments:
                    if a.stage in self.stage_combos:
                        idx = self.stage_combos[a.stage].findData(a.employee_id)
                        if idx >= 0:
                            self.stage_combos[a.stage].setCurrentIndex(idx)

    def add_new_client(self):
        dlg = ClientSelectDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
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

    def get_materials_data(self):
        """Get materials from table."""
        result = []
        for row in range(self.materials_table.rowCount()):
            c0 = self.materials_table.cellWidget(row, 0)
            c1 = self.materials_table.cellWidget(row, 1)
            c2 = self.materials_table.cellWidget(row, 2)
            if c0 and c1 and c2:
                mat_id = c0.currentData()
                if mat_id and c1.value() > 0:
                    result.append((mat_id, c1.value(), c2.value()))
        return result

    def get_assignments_data(self):
        """Get stage assignments."""
        return [(sid, c.currentData()) for sid, c in self.stage_combos.items() if c.currentData()]


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

        btn_row2 = QHBoxLayout()
        edit_btn = QPushButton("Редактировать")
        edit_btn.clicked.connect(self.edit_order)
        print_btn = QPushButton("Печать счёта")
        print_btn.setObjectName("secondary")
        print_btn.clicked.connect(self.print_invoice)
        btn_row2.addWidget(edit_btn)
        btn_row2.addWidget(print_btn)
        layout.addLayout(btn_row2)

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
        if dlg.exec() == QDialog.DialogCode.Accepted:
            with get_db() as db:
                order = Order(**dlg.get_data())
                db.add(order)
                db.flush()
                _save_order_extras(db, order, dlg)
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
            if dlg.exec() == QDialog.DialogCode.Accepted:
                data = dlg.get_data()
                for k, v in data.items():
                    setattr(order, k, v)
                if order.status == "ready" and not order.completed_at:
                    order.completed_at = datetime.utcnow()
                _save_order_extras(db, order, dlg)
                db.commit()
                self.load_data()
                if self.main_window:
                    self.main_window.show_toast("Заказ обновлён")

    def print_invoice(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Информация", "Выберите заказ")
            return
        order_id = self.table.item(row, 0).data(Qt.UserRole)
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить счёт", "", "PDF (*.pdf)")
        if not path:
            return
        with get_db() as db:
            order = db.query(Order).get(order_id)
            if not order:
                return
            client = db.query(Client).get(order.client_id)
            materials = []
            for om in order.materials:
                mat = db.query(Material).get(om.material_id)
                materials.append({
                    "name": mat.name if mat else "-",
                    "quantity": om.quantity,
                    "price": om.unit_price or 0,
                })
            export_order_invoice({
                "id": order.id,
                "client_name": client.full_name if client else "-",
                "date": order.created_at.strftime("%d.%m.%Y") if order.created_at else "",
                "materials": materials,
                "total": order.total_amount or 0,
            }, path)
        QMessageBox.information(self, "Готово", "Счёт сохранён")
