"""Load test/demo data for atelier application."""
import bcrypt
from datetime import datetime, date, timedelta
import random

from database.session import SessionLocal, init_db
from database.models import (
    Role, User, Employee, Client, Order, OrderItem, OrderAssignment,
    Material, OrderMaterial, WorkLog, Expense, ExpenseCategory, SalaryRecord
)
from database.init_data import seed_roles, seed_expense_categories


def clear_test_data(session):
    """Clear all data except roles and admin user."""
    session.query(SalaryRecord).delete()
    session.query(WorkLog).delete()
    session.query(OrderMaterial).delete()
    session.query(OrderItem).delete()
    session.query(OrderAssignment).delete()
    session.query(Order).delete()
    session.query(Expense).delete()
    session.query(Client).delete()
    session.query(Employee).delete()
    # Keep admin user
    session.query(User).filter(User.username != "admin").delete()
    session.commit()


def load_test_data():
    """Load comprehensive test data."""
    init_db()
    db = SessionLocal()
    try:
        clear_test_data(db)
        seed_roles(db)
        seed_expense_categories(db)

        # Ensure admin and manager exist
        pw_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
        for username, role_name in [("admin", "admin"), ("manager", "manager")]:
            if not db.query(User).filter_by(username=username).first():
                role = db.query(Role).filter_by(name=role_name).first()
                if role:
                    db.add(User(username=username, password_hash=pw_hash, role_id=role.id))

        # Employees
        employees_data = [
            ("Анна Петрова", "designer", 35000, 5, 500),
            ("Мария Сидорова", "constructor", 40000, 7, 600),
            ("Елена Козлова", "cutter", 30000, 4, 450),
            ("Ольга Новикова", "tailor", 32000, 6, 550),
            ("Ирина Морозова", "tailor", 28000, 5, 480),
        ]
        employees = []
        for name, pos, base, pct, hourly in employees_data:
            emp = Employee(full_name=name, position=pos, base_salary=base,
                          order_percent=pct, hourly_rate=hourly,
                          phone=f"+7 9{random.randint(10,99)} {random.randint(100,999)}-{random.randint(10,99)}-{random.randint(10,99)}")
            db.add(emp)
            db.flush()
            employees.append(emp)

        # Clients
        clients_data = [
            ("Смирнова Татьяна", "+7 916 123-45-67"),
            ("Кузнецов Андрей", "+7 903 234-56-78"),
            ("Попова Екатерина", "+7 926 345-67-89"),
            ("Васильев Дмитрий", "+7 495 456-78-90"),
            ("Михайлова Анна", "+7 916 567-89-01"),
            ("Новиков Сергей", "+7 903 678-90-12"),
            ("Федорова Ольга", "+7 926 789-01-23"),
        ]
        clients = []
        for name, phone in clients_data:
            c = Client(full_name=name, phone=phone)
            db.add(c)
            db.flush()
            clients.append(c)

        # Materials
        materials_data = [
            ("Шёлк атлас", "Ткань", "м", 1200, 50),
            ("Хлопок сатин", "Ткань", "м", 450, 100),
            ("Шерсть кашемир", "Ткань", "м", 2500, 30),
            ("Лён", "Ткань", "м", 600, 80),
            ("Молнии", "Фурнитура", "шт", 50, 200),
            ("Пуговицы", "Фурнитура", "уп", 120, 50),
            ("Нитки", "Прочее", "кат", 80, 100),
        ]
        materials = []
        for name, cat, unit, price, qty in materials_data:
            m = Material(name=name, category=cat, unit=unit, price_per_unit=price, quantity=qty)
            db.add(m)
            db.flush()
            materials.append(m)

        # Orders with various statuses
        statuses = ["accepted", "design", "construction", "cutting", "sewing", "ready"]
        today = date.today()
        for i in range(15):
            client = random.choice(clients)
            status = statuses[min(i % 6, 5)]
            deadline = today + timedelta(days=random.randint(5, 30))
            amount = random.randint(5000, 50000)
            order = Order(
                client_id=client.id,
                status=status,
                total_amount=amount,
                description=f"Заказ #{i+1}: платье/костюм",
                deadline=deadline,
                completed_at=datetime.utcnow() - timedelta(days=random.randint(0, 10)) if status == "ready" else None
            )
            db.add(order)
            db.flush()

            # Assign employees to stages
            for stage in ["design", "construction", "cutting", "sewing"]:
                emp = random.choice(employees)
                db.add(OrderAssignment(order_id=order.id, employee_id=emp.id, stage=stage))

            # Work logs for some orders
            if random.random() > 0.5:
                emp = random.choice(employees)
                db.add(WorkLog(employee_id=emp.id, order_id=order.id, hours=random.uniform(2, 8),
                               date=today - timedelta(days=random.randint(0, 14))))

        # Expenses
        categories = list(db.query(ExpenseCategory).all())
        for _ in range(20):
            cat = random.choice(categories)
            exp_date = today - timedelta(days=random.randint(0, 60))
            db.add(Expense(category_id=cat.id, amount=random.randint(500, 50000),
                           date=exp_date, description=f"Расход: {cat.name}"))

        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
