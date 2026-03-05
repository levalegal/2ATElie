"""Dashboard widget with stats and charts."""
from datetime import date, timedelta
from collections import defaultdict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QGroupBox, QDateEdit, QPushButton, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtCore import QSettings
from sqlalchemy import func

from database.session import get_db
from database.models import Order, Expense, Employee
from config.settings import ORDER_STATUSES
from utils.export import export_dashboard_to_pdf

try:
    import pyqtgraph as pg
    HAS_PYQTGRAPH = True
except ImportError:
    HAS_PYQTGRAPH = False


def get_card_style(dark=True):
    if dark:
        bg = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2d2d30, stop:1 #252528)"
        val_color = "#c45c5c"
        lbl_color = "#9a9a9d"
        border = "1px solid #3d3d40"
    else:
        bg = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #fafafa)"
        val_color = "#8b3a3a"
        lbl_color = "#6b6b6b"
        border = "1px solid #e0e0e0"
    return f"""
        QFrame {{
            background: {bg};
            border-radius: 16px;
            border: {border};
            padding: 20px;
        }}
        QLabel#value {{ font-size: 28px; font-weight: bold; color: {val_color}; }}
        QLabel#label {{ font-size: 13px; color: {lbl_color}; }}
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
        export_pdf_btn = QPushButton("Экспорт в PDF")
        export_pdf_btn.setObjectName("secondary")
        export_pdf_btn.clicked.connect(self.export_pdf)
        period_layout.addWidget(refresh_btn)
        period_layout.addWidget(export_pdf_btn)
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

        self.stat_cards = []
        for i, (title, label_widget) in enumerate([
            ("Выручка", self.revenue_label),
            ("Затраты", self.expenses_label),
            ("Прибыль", self.profit_label),
            ("Заказов", self.orders_label),
        ]):
            card = QFrame()
            theme = QSettings("Atelier", "2ATElie").value("theme", "dark")
            card.setStyleSheet(get_card_style(theme == "dark"))
            card_layout = QVBoxLayout(card)
            card_layout.addWidget(QLabel(title, objectName="label"))
            card_layout.addWidget(label_widget)
            cards_layout.addWidget(card, 0, i)
            self.stat_cards.append(card)

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

        # Chart
        if HAS_PYQTGRAPH:
            self.chart_widget = pg.PlotWidget()
            self.chart_widget.setBackground("#1a1a1d")
            self.chart_widget.setMinimumHeight(200)
            layout.addWidget(QLabel("Выручка и затраты по месяцам"))
            layout.addWidget(self.chart_widget)
        else:
            self.chart_widget = None

    def _apply_card_theme(self):
        theme = QSettings("Atelier", "2ATElie").value("theme", "dark")
        style = get_card_style(theme == "dark")
        for card in getattr(self, "stat_cards", []):
            card.setStyleSheet(style)

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

        # Update chart
        if HAS_PYQTGRAPH and self.chart_widget:
            self._update_chart(start, end)

    def quick_new_order(self):
        if self.main_window and "orders" in self.main_window.pages:
            self.main_window.navigate_to("orders")
            self.main_window.pages["orders"].add_order()

    def quick_add_expense(self):
        if self.main_window and "expenses" in self.main_window.pages:
            self.main_window.navigate_to("expenses")
            self.main_window.pages["expenses"].add_expense()

    def export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить отчёт", "", "PDF (*.pdf)")
        if not path:
            return
        start = self.period_start.date().toPython()
        end = self.period_end.date().toPython()
        period_str = f"{start.strftime('%d.%m.%Y')} — {end.strftime('%d.%m.%Y')}"
        revenue = self.revenue_label.text().replace("\u202f", "").replace(" ", "")
        expenses = self.expenses_label.text().replace("\u202f", "").replace(" ", "")
        profit = self.profit_label.text().replace("\u202f", "").replace(" ", "")
        items = [
            ("Выручка", revenue),
            ("Затраты", expenses),
            ("Прибыль", profit),
            ("Заказов", self.orders_label.text()),
        ]
        for k, v in self.status_labels.items():
            items.append((ORDER_STATUSES.get(k, k), v.text()))
        export_dashboard_to_pdf({"period": period_str, "items": items}, path)
        QMessageBox.information(self, "Готово", "Отчёт сохранён")

    def _update_chart(self, start: date, end: date):
        """Update revenue/expenses chart by month."""
        months_rev = defaultdict(float)
        months_exp = defaultdict(float)
        with get_db() as db:
            for o in db.query(Order).filter(Order.status == "ready").all():
                dt = o.completed_at or o.updated_at
                if dt and start <= dt.date() <= end:
                    key = (dt.year, dt.month)
                    months_rev[key] += o.total_amount or 0
            for e in db.query(Expense).filter(
                Expense.date >= start,
                Expense.date <= end
            ).all():
                key = (e.date.year, e.date.month)
                months_exp[key] += e.amount or 0
        keys = sorted(set(months_rev.keys()) | set(months_exp.keys()))
        if not keys:
            return
        labels = [f"{k[1]:02d}.{k[0]}" for k in keys]
        x = list(range(len(keys)))
        rev_vals = [months_rev[k] for k in keys]
        exp_vals = [months_exp[k] for k in keys]
        self.chart_widget.clear()
        x_rev = [i - 0.2 for i in x]
        x_exp = [i + 0.2 for i in x]
        bg = pg.BarGraphItem(x=x_rev, height=rev_vals, width=0.35, brush="#8b3a3a")
        self.chart_widget.addItem(bg)
        bg2 = pg.BarGraphItem(x=x_exp, height=exp_vals, width=0.35, brush="#5a5a5d")
        self.chart_widget.addItem(bg2)
        ax = self.chart_widget.getAxis("bottom")
        ax.setTicks([list(zip(x, labels))])
