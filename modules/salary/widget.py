"""Salary calculation and records widget."""
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QDateEdit, QMessageBox,
    QAbstractItemView, QGroupBox, QFormLayout, QLabel, QFileDialog
)
from PySide6.QtCore import Qt
from database.session import get_db
from database.models import Employee, Order, OrderAssignment, WorkLog, SalaryRecord
from utils.export import export_salary_to_excel, export_salary_to_pdf


def calculate_salary_for_employee(db, employee_id: int, period_start: date, period_end: date) -> dict:
    """Calculate salary for employee in period."""
    emp = db.query(Employee).get(employee_id)
    if not emp:
        return {}
    base = emp.base_salary or 0
    order_pct = emp.order_percent or 0
    hourly = emp.hourly_rate or 0

    # Orders completed in period where employee was assigned
    order_amount = 0
    assignments = db.query(OrderAssignment).filter(
        OrderAssignment.employee_id == employee_id,
        OrderAssignment.stage.in_(["design", "construction", "cutting", "sewing"])
    ).all()
    for a in assignments:
        order = db.query(Order).filter(
            Order.id == a.order_id,
            Order.status == "ready"
        ).first()
        if not order or not order.completed_at:
            continue
        ord_date = order.completed_at.date() if hasattr(order.completed_at, 'date') else order.completed_at
        if period_start <= ord_date <= period_end and order.total_amount:
            order_amount += order.total_amount * (order_pct / 100)

    # Hourly from work logs
    hourly_amount = 0
    logs = db.query(WorkLog).filter(
        WorkLog.employee_id == employee_id,
        WorkLog.date >= period_start,
        WorkLog.date <= period_end
    ).all()
    for log in logs:
        hourly_amount += (log.hours or 0) * hourly

    total = base + order_amount + hourly_amount
    return {
        "base": base,
        "order_amount": order_amount,
        "hourly_amount": hourly_amount,
        "total": total,
    }


class SalaryWidget(QWidget):
    """Salary calculation and payroll."""

    def __init__(self, main_window=None):
        super().__init__(main_window)
        self.main_window = main_window
        self.setup_ui()
        self.calculate()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        # Period selector
        period_group = QGroupBox("Период")
        period_layout = QFormLayout(period_group)
        self.period_start = QDateEdit()
        self.period_start.setCalendarPopup(True)
        self.period_end = QDateEdit()
        self.period_end.setCalendarPopup(True)
        # Default: current month
        today = date.today()
        self.period_start.setDate(today.replace(day=1))
        self.period_end.setDate(today)
        period_layout.addRow("С:", self.period_start)
        period_layout.addRow("По:", self.period_end)
        calc_btn = QPushButton("Рассчитать")
        calc_btn.clicked.connect(self.calculate)
        period_layout.addRow(calc_btn)
        layout.addWidget(period_group)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Сотрудник", "Должность", "База", "От заказов", "По часам", "Итого"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить ведомость")
        save_btn.clicked.connect(self.save_payroll)
        export_excel_btn = QPushButton("Экспорт в Excel")
        export_excel_btn.setObjectName("secondary")
        export_excel_btn.clicked.connect(self.export_excel)
        export_pdf_btn = QPushButton("Экспорт в PDF")
        export_pdf_btn.setObjectName("secondary")
        export_pdf_btn.clicked.connect(self.export_pdf)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(export_excel_btn)
        btn_layout.addWidget(export_pdf_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def calculate(self):
        start = self.period_start.date().toPython()
        end = self.period_end.date().toPython()
        with get_db() as db:
            employees = db.query(Employee).order_by(Employee.full_name).all()
            self.table.setRowCount(len(employees))
            for i, emp in enumerate(employees):
                calc = calculate_salary_for_employee(db, emp.id, start, end)
                self.table.setItem(i, 0, QTableWidgetItem(emp.full_name))
                self.table.setItem(i, 1, QTableWidgetItem(emp.position))
                self.table.setItem(i, 2, QTableWidgetItem(f"{calc.get('base', 0):,.0f}"))
                self.table.setItem(i, 3, QTableWidgetItem(f"{calc.get('order_amount', 0):,.0f}"))
                self.table.setItem(i, 4, QTableWidgetItem(f"{calc.get('hourly_amount', 0):,.0f}"))
                self.table.setItem(i, 5, QTableWidgetItem(f"{calc.get('total', 0):,.0f}"))
                self.table.item(i, 0).setData(Qt.UserRole, (emp.id, calc))

    def save_payroll(self):
        start = self.period_start.date().toPython()
        end = self.period_end.date().toPython()
        with get_db() as db:
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)
                if not item:
                    continue
                emp_id, calc = item.data(Qt.UserRole)
                if not calc or calc.get("total", 0) <= 0:
                    continue
                existing = db.query(SalaryRecord).filter(
                    SalaryRecord.employee_id == emp_id,
                    SalaryRecord.period_start == start,
                    SalaryRecord.period_end == end
                ).first()
                if existing:
                    existing.base_amount = calc["base"]
                    existing.order_amount = calc["order_amount"]
                    existing.hourly_amount = calc["hourly_amount"]
                    existing.total = calc["total"]
                else:
                    rec = SalaryRecord(
                        employee_id=emp_id,
                        period_start=start,
                        period_end=end,
                        base_amount=calc["base"],
                        order_amount=calc["order_amount"],
                        hourly_amount=calc["hourly_amount"],
                        total=calc["total"],
                    )
                    db.add(rec)
            db.commit()
        QMessageBox.information(self, "Готово", "Ведомость сохранена")

    def export_excel(self):
        start = self.period_start.date().toPython()
        end = self.period_end.date().toPython()
        records = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if not item:
                continue
            _, calc = item.data(Qt.UserRole)
            if not calc:
                continue
            records.append({
                "name": self.table.item(row, 0).text(),
                "position": self.table.item(row, 1).text(),
                "base": calc.get("base", 0),
                "order_amount": calc.get("order_amount", 0),
                "hourly_amount": calc.get("hourly_amount", 0),
                "total": calc.get("total", 0),
            })
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт", "", "Excel (*.xlsx)")
        if path:
            export_salary_to_excel(records, path, start, end)
            QMessageBox.information(self, "Готово", "Файл сохранён")

    def export_pdf(self):
        start = self.period_start.date().toPython()
        end = self.period_end.date().toPython()
        records = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if not item:
                continue
            _, calc = item.data(Qt.UserRole)
            if not calc:
                continue
            records.append({
                "name": self.table.item(row, 0).text(),
                "position": self.table.item(row, 1).text(),
                "base": calc.get("base", 0),
                "order_amount": calc.get("order_amount", 0),
                "hourly_amount": calc.get("hourly_amount", 0),
                "total": calc.get("total", 0),
            })
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт", "", "PDF (*.pdf)")
        if path:
            export_salary_to_pdf(records, path, start, end)
            QMessageBox.information(self, "Готово", "Файл сохранён")
