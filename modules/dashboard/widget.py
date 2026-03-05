"""Dashboard widget with stats and charts."""
from datetime import date, timedelta

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QGroupBox, QDateEdit, QPushButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from sqlalchemy import func

from database.session import get_db
from database.models import Order, Expense, Employee
from config.settings import ORDER_STATUSES


def get_card_style(dark=True):
    bg = "#2d2d30" if dark else "#ffffff"
    val_color = "#8b3a3a"
    lbl_color = "#9a9a9d" if dark else "#6b6b6b"
    border = "1px solid #3d3d40" if dark else "1px solid #e0e0e0"
    return f"""
        QFrame {{
            background-color: {bg};
            border-radius: 14px;
            border: {border};
            padding: 18px;
        }}
        QLabel#value {{ font-size: 26px; font-weight: bold; color: {val_color}; }}
        QLabel#label {{ font-size: 12px; color: {lbl_color}; }}
    """


class DashboardWidget(QWidget):
    """Dashboard with revenue, expenses, orders overview."""

    def __init__(self, main_window=None):
        super().__init__(main_window)
        self.main_window = main_window
        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        # Period
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("Период:"))
        self.period_start = QDateEdit()
        self.period_start.setCalendarPopup(True)
        self.period_end = QDateEdit()
        self.period_end.setCalendarPopup(True)
        today = date.today()
        self.period_start.setDate(today.replace(day=1))
        self.period_end.setDate(today)
        period_layout.addWidget(self.period_start)
        period_layout.addWidget(QLabel("—"))
        period_layout.addWidget(self.period_end)
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.refresh)
        period_layout.addWidget(refresh_btn)
        # Quick actions
        new_order_btn = QPushButton("+ Новый заказ")
        new_order_btn.clicked.connect(self.quick_new_order)
        add_expense_btn = QPushButton("+ Добавить расход")
        add_expense_btn.setObjectName("secondary")
        add_expense_btn.clicked.connect(self.quick_add_expense)
        period_layout.addWidget(new_order_btn)
        period_layout.addWidget(add_expense_btn)
        period_layout.addStretch()
        layout.addLayout(period_layout)

        # Stats cards
        cards_layout = QGridLayout()
        self.revenue_label = QLabel("0")
        self.revenue_label.setObjectName("value")
        self.expenses_label = QLabel("0")
        self.expenses_label.setObjectName("value")
        self.profit_label = QLabel("0")
        self.profit_label.setObjectName("value")
        self.orders_label = QLabel("0")
        self.orders_label.setObjectName("value")

        for i, (title, label_widget) in enumerate([
            ("Выручка", self.revenue_label),
            ("Затраты", self.expenses_label),
            ("Прибыль", self.profit_label),
            ("Заказов", self.orders_label),
        ]):
            card = QFrame()
            card.setStyleSheet(get_card_style(True))
            card_layout = QVBoxLayout(card)
            card_layout.addWidget(QLabel(title, objectName="label"))
            card_layout.addWidget(label_widget)
            cards_layout.addWidget(card, 0, i)

        layout.addLayout(cards_layout)

        # Orders by status
        status_group = QGroupBox("Заказы по статусам")
        status_layout = QVBoxLayout(status_group)
        self.status_labels = {}
        for status_key, status_name in ORDER_STATUSES.items():
            row = QHBoxLayout()
            lbl = QLabel(f"{status_name}:")
            val = QLabel("0")
            val.setObjectName("value")
            row.addWidget(lbl)
            row.addWidget(val)
            row.addStretch()
            status_layout.addLayout(row)
            self.status_labels[status_key] = val
        layout.addWidget(status_group)

    def refresh(self):
        start = self.period_start.date().toPython()
        end = self.period_end.date().toPython()
        with get_db() as db:
            # Revenue from completed orders (use completed_at or updated_at)
            revenue_result = db.query(Order).filter(Order.status == "ready").all()
            revenue = 0
            for o in revenue_result:
                dt = o.completed_at or o.updated_at
                if dt and start <= dt.date() <= end:
                    revenue += o.total_amount or 0

            # Expenses
            expenses = db.query(func.sum(Expense.amount)).filter(
                Expense.date >= start,
                Expense.date <= end
            ).scalar() or 0

            # Orders count
            orders_count = db.query(func.count(Order.id)).filter(
                func.date(Order.created_at) >= start,
                func.date(Order.created_at) <= end
            ).scalar() or 0

        self.revenue_label.setText(f"{revenue:,.0f} ₽")
        self.expenses_label.setText(f"{expenses:,.0f} ₽")
        self.profit_label.setText(f"{revenue - expenses:,.0f} ₽")
        self.orders_label.setText(str(orders_count))

        with get_db() as db:
            for status_key in ORDER_STATUSES:
                cnt = db.query(func.count(Order.id)).filter(Order.status == status_key).scalar() or 0
                self.status_labels[status_key].setText(str(cnt))

    def quick_new_order(self):
        if self.main_window and "orders" in self.main_window.pages:
            self.main_window.navigate_to("orders")
            self.main_window.pages["orders"].add_order()

    def quick_add_expense(self):
        if self.main_window and "expenses" in self.main_window.pages:
            self.main_window.navigate_to("expenses")
            self.main_window.pages["expenses"].add_expense()
