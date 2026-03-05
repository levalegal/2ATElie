"""Salary calculation and records widget."""
from datetime import datetime, date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QDateEdit, QMessageBox,
    QAbstractItemView, QGroupBox, QFormLayout, QLabel, QFileDialog,
    QTabWidget, QDialog, QDoubleSpinBox
)
from PySide6.QtCore import Qt
from database.session import get_db
from database.models import Employee, Order, OrderAssignment, WorkLog, SalaryRecord
from database.models import Client
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
        self.load_history()
        self.load_worklogs()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        # Tab 1: Calculation
        calc_tab = QWidget()
        calc_layout = QVBoxLayout(calc_tab)
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
        calc_layout.addWidget(period_group)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Сотрудник", "Должность", "База", "От заказов", "По часам", "Итого"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        calc_layout.addWidget(self.table)

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
        calc_layout.addLayout(btn_layout)
        self.tabs.addTab(calc_tab, "Расчёт")

        # Tab 2: History
        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels(
            ["Сотрудник", "Период", "База", "От заказов", "По часам", "Итого", "Выплачено"]
        )
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.history_table.doubleClicked.connect(self.toggle_paid)
        history_layout.addWidget(self.history_table)
        btn_row = QHBoxLayout()
        mark_paid_btn = QPushButton("Отметить выплачено / снять отметку")
        mark_paid_btn.clicked.connect(self.toggle_paid)
        detail_btn = QPushButton("Детализация по заказам")
        detail_btn.setObjectName("secondary")
        detail_btn.clicked.connect(self.show_salary_detail)
        refresh_history_btn = QPushButton("Обновить")
        refresh_history_btn.setObjectName("secondary")
        refresh_history_btn.clicked.connect(self.load_history)
        btn_row.addWidget(mark_paid_btn)
        btn_row.addWidget(detail_btn)
        btn_row.addWidget(refresh_history_btn)
        history_layout.addLayout(btn_row)
        self.tabs.addTab(history_tab, "История начислений")

        # Tab 3: Work Log (учёт времени)
        worklog_tab = QWidget()
        wl_layout = QVBoxLayout(worklog_tab)
        wl_form = QFormLayout()
        self.wl_employee = QComboBox()
        self.wl_employee.addItem("— Выберите —", None)
        with get_db() as db:
            for e in db.query(Employee).order_by(Employee.full_name).all():
                self.wl_employee.addItem(e.full_name, e.id)
        self.wl_order = QComboBox()
        self.wl_order.addItem("— Выберите —", None)
        self._refresh_wl_orders()
        self.wl_hours = QDoubleSpinBox()
        self.wl_hours.setRange(0.5, 24)
        self.wl_hours.setSingleStep(0.5)
        self.wl_date = QDateEdit()
        self.wl_date.setCalendarPopup(True)
        self.wl_date.setDate(date.today())
        wl_form.addRow("Сотрудник:", self.wl_employee)
        wl_form.addRow("Заказ:", self.wl_order)
        wl_form.addRow("Часы:", self.wl_hours)
        wl_form.addRow("Дата:", self.wl_date)
        wl_layout.addLayout(wl_form)
        add_wl_btn = QPushButton("+ Добавить учёт времени")
        add_wl_btn.clicked.connect(self.add_work_log)
        wl_layout.addWidget(add_wl_btn)
        self.worklog_table = QTableWidget()
        self.worklog_table.setColumnCount(5)
        self.worklog_table.setHorizontalHeaderLabels(["Сотрудник", "Заказ", "Часы", "Дата", ""])
        self.worklog_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        wl_layout.addWidget(self.worklog_table)
        self.tabs.addTab(worklog_tab, "Учёт времени")

        layout.addWidget(self.tabs)

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
        if self.main_window:
            self.main_window.show_toast("Ведомость сохранена")
        else:
            QMessageBox.information(self, "Готово", "Ведомость сохранена")
        self.load_history()

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

    def load_history(self):
        """Load salary records history."""
        with get_db() as db:
            records = db.query(SalaryRecord).order_by(
                SalaryRecord.period_end.desc()
            ).all()
            self.history_table.setRowCount(len(records))
            for i, rec in enumerate(records):
                emp = db.query(Employee).get(rec.employee_id)
                emp_name = emp.full_name if emp else "-"
                period = f"{rec.period_start.strftime('%d.%m')} — {rec.period_end.strftime('%d.%m.%Y')}"
                self.history_table.setItem(i, 0, QTableWidgetItem(emp_name))
                self.history_table.setItem(i, 1, QTableWidgetItem(period))
                self.history_table.setItem(i, 2, QTableWidgetItem(f"{rec.base_amount:,.0f}"))
                self.history_table.setItem(i, 3, QTableWidgetItem(f"{rec.order_amount:,.0f}"))
                self.history_table.setItem(i, 4, QTableWidgetItem(f"{rec.hourly_amount:,.0f}"))
                self.history_table.setItem(i, 5, QTableWidgetItem(f"{rec.total:,.0f}"))
                self.history_table.setItem(i, 6, QTableWidgetItem("Да" if rec.paid else "Нет"))
                self.history_table.item(i, 0).setData(Qt.UserRole, rec.id)

    def toggle_paid(self):
        """Toggle paid status for selected salary record."""
        row = self.history_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Информация", "Выберите запись")
            return
        rec_id = self.history_table.item(row, 0).data(Qt.UserRole)
        with get_db() as db:
            rec = db.query(SalaryRecord).get(rec_id)
            if rec:
                rec.paid = not rec.paid
                rec.paid_at = datetime.utcnow() if rec.paid else None
                db.commit()
                self.load_history()
                if self.main_window:
                    self.main_window.show_toast("Статус обновлён")

    def show_salary_detail(self):
        """Show salary breakdown by orders for selected record."""
        row = self.history_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Информация", "Выберите запись")
            return
        rec_id = self.history_table.item(row, 0).data(Qt.UserRole)
        dlg = QDialog(self)
        dlg.setWindowTitle("Детализация начисления")
        dlg.setMinimumSize(500, 400)
        layout = QVBoxLayout(dlg)
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Заказ", "Клиент", "Сумма заказа", "Начислено"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(table)
        with get_db() as db:
            rec = db.query(SalaryRecord).get(rec_id)
            if not rec:
                return
            emp = db.query(Employee).get(rec.employee_id)
            pct = emp.order_percent or 0
            assignments = db.query(OrderAssignment).filter(
                OrderAssignment.employee_id == rec.employee_id,
                OrderAssignment.stage.in_(["design", "construction", "cutting", "sewing"])
            ).all()
            rows = []
            for a in assignments:
                o = db.query(Order).get(a.order_id)
                if not o or o.status != "ready" or not o.total_amount:
                    continue
                dt = o.completed_at or o.updated_at
                if not dt or not (rec.period_start <= dt.date() <= rec.period_end):
                    continue
                c = db.query(Client).get(o.client_id)
                amt = o.total_amount * (pct / 100)
                rows.append((o.id, c.full_name if c else "-", o.total_amount, amt))
            seen = set()
            unique = []
            for oid, cname, tot, amt in rows:
                if oid not in seen:
                    seen.add(oid)
                    unique.append((oid, cname, tot, amt))
            table.setRowCount(len(unique))
            for i, (oid, cname, tot, amt) in enumerate(unique):
                table.setItem(i, 0, QTableWidgetItem(f"#{oid}"))
                table.setItem(i, 1, QTableWidgetItem(cname))
                table.setItem(i, 2, QTableWidgetItem(f"{tot:,.0f} ₽"))
                table.setItem(i, 3, QTableWidgetItem(f"{amt:,.0f} ₽"))
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn)
        dlg.exec()

    def _refresh_wl_orders(self):
        self.wl_order.clear()
        self.wl_order.addItem("— Выберите —", None)
        with get_db() as db:
            from database.models import Order as Ord, Client
            for o in db.query(Ord).order_by(Ord.created_at.desc()).limit(50).all():
                c = db.query(Client).get(o.client_id)
                name = f"#{o.id} {c.full_name}" if c else f"#{o.id}"
                self.wl_order.addItem(name, o.id)

    def add_work_log(self):
        emp_id = self.wl_employee.currentData()
        order_id = self.wl_order.currentData()
        if not emp_id or not order_id:
            QMessageBox.warning(self, "Ошибка", "Выберите сотрудника и заказ")
            return
        with get_db() as db:
            db.add(WorkLog(
                employee_id=emp_id,
                order_id=order_id,
                hours=self.wl_hours.value(),
                date=self.wl_date.date().toPython(),
            ))
            db.commit()
        self.load_worklogs()
        if self.main_window:
            self.main_window.show_toast("Учёт времени добавлен")

    def load_worklogs(self):
        self._refresh_wl_orders()
        with get_db() as db:
            from database.models import Order as Ord, Client
            logs = db.query(WorkLog).order_by(WorkLog.date.desc()).limit(100).all()
            self.worklog_table.setRowCount(len(logs))
            for i, log in enumerate(logs):
                emp = db.query(Employee).get(log.employee_id)
                order = db.query(Ord).get(log.order_id)
                c = db.query(Client).get(order.client_id) if order else None
                self.worklog_table.setItem(i, 0, QTableWidgetItem(emp.full_name if emp else "-"))
                self.worklog_table.setItem(i, 1, QTableWidgetItem(f"#{log.order_id} {c.full_name}" if c else f"#{log.order_id}"))
                self.worklog_table.setItem(i, 2, QTableWidgetItem(str(log.hours)))
                self.worklog_table.setItem(i, 3, QTableWidgetItem(log.date.strftime("%d.%m.%Y") if log.date else "-"))
                del_btn = QPushButton("✕")
                del_btn.setMaximumWidth(30)
                del_btn.setProperty("log_id", log.id)
                del_btn.clicked.connect(self._delete_worklog)
                self.worklog_table.setCellWidget(i, 4, del_btn)

    def _delete_worklog(self):
        btn = self.sender()
        if btn and btn.property("log_id"):
            if QMessageBox.question(self, "Подтверждение", "Удалить запись?",
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
                with get_db() as db:
                    rec = db.query(WorkLog).get(btn.property("log_id"))
                    if rec:
                        db.delete(rec)
                    db.commit()
                self.load_worklogs()
