"""Materials module widget."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QLineEdit,
    QDoubleSpinBox, QComboBox, QMessageBox, QAbstractItemView
)
from PySide6.QtCore import Qt

from database.session import get_db
from database.models import Material


class MaterialEditDialog(QDialog):
    """Add/Edit material dialog."""

    def __init__(self, parent=None, material: Material = None):
        super().__init__(parent)
        self.material = material
        self.setWindowTitle("Редактировать материал" if material else "Добавить материал")
        self.setMinimumWidth(400)
        self.setup_ui()
        if material:
            self.load_data()

    def setup_ui(self):
        layout = QFormLayout(self)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Название")
        layout.addRow("Название:", self.name_edit)

        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems(["Ткань", "Фурнитура", "Нитки", "Прочее"])
        layout.addRow("Категория:", self.category_combo)

        self.unit_edit = QLineEdit()
        self.unit_edit.setPlaceholderText("м")
        self.unit_edit.setText("м")
        layout.addRow("Единица:", self.unit_edit)

        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 1000000)
        self.price_spin.setSuffix(" ₽")
        layout.addRow("Цена за ед.:", self.price_spin)

        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0, 1000000)
        layout.addRow("Остаток:", self.quantity_spin)

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
        m = self.material
        self.name_edit.setText(m.name)
        self.category_combo.setCurrentText(m.category or "Ткань")
        self.unit_edit.setText(m.unit or "м")
        self.price_spin.setValue(m.price_per_unit or 0)
        self.quantity_spin.setValue(m.quantity or 0)

    def save(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите название")
            return
        self.accept()

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "category": self.category_combo.currentText() or None,
            "unit": self.unit_edit.text().strip() or "м",
            "price_per_unit": self.price_spin.value(),
            "quantity": self.quantity_spin.value(),
        }


class MaterialsWidget(QWidget):
    """Materials list and management."""

    def __init__(self, main_window=None):
        super().__init__(main_window)
        self.main_window = main_window
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+ Добавить материал")
        add_btn.clicked.connect(self.add_material)
        btn_layout.addWidget(add_btn)
        btn_layout.addStretch()
        refresh_btn = QPushButton("Обновить")
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self.load_data)
        btn_layout.addWidget(refresh_btn)
        layout.addLayout(btn_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Название", "Категория", "Ед.", "Цена", "Остаток"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.doubleClicked.connect(self.edit_material)
        layout.addWidget(self.table)

        edit_btn = QPushButton("Редактировать")
        edit_btn.clicked.connect(self.edit_material)
        layout.addWidget(edit_btn)

    def load_data(self):
        with get_db() as db:
            materials = db.query(Material).order_by(Material.name).all()
            self.table.setRowCount(len(materials))
            for i, m in enumerate(materials):
                self.table.setItem(i, 0, QTableWidgetItem(m.name))
                self.table.setItem(i, 1, QTableWidgetItem(m.category or ""))
                self.table.setItem(i, 2, QTableWidgetItem(m.unit or "м"))
                self.table.setItem(i, 3, QTableWidgetItem(f"{m.price_per_unit or 0:,.0f} ₽"))
                self.table.setItem(i, 4, QTableWidgetItem(f"{m.quantity or 0}"))
                self.table.item(i, 0).setData(Qt.UserRole, m.id)

    def add_material(self):
        dlg = MaterialEditDialog(self)
        if dlg.exec() == dlg.Accepted:
            with get_db() as db:
                mat = Material(**dlg.get_data())
                db.add(mat)
                db.commit()
            self.load_data()

    def edit_material(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Информация", "Выберите материал")
            return
        mat_id = self.table.item(row, 0).data(Qt.UserRole)
        with get_db() as db:
            mat = db.query(Material).get(mat_id)
            if not mat:
                return
            dlg = MaterialEditDialog(self, mat)
            if dlg.exec() == dlg.Accepted:
                data = dlg.get_data()
                for k, v in data.items():
                    setattr(mat, k, v)
                db.commit()
                self.load_data()
