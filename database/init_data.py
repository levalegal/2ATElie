"""Initialize database with default data."""
import bcrypt
import random
from datetime import datetime, date, timedelta

from database.session import SessionLocal, init_db
from database.models import (
    Role, User, ExpenseCategory, Employee, Client, Order,
    OrderAssignment, Material, Expense, WorkLog
)


def seed_roles(session):
    """Create default roles."""
    roles_data = [
        ("admin", "Админ"),
        ("manager", "Руководитель"),
        ("designer", "Дизайнер"),
        ("constructor", "Модельер-конструктор"),
        ("cutter", "Закройщик"),
        ("tailor", "Портной"),
    ]
    for name, display in roles_data:
        if not session.query(Role).filter_by(name=name).first():
            session.add(Role(name=name, display_name=display))
    session.commit()


def seed_admin(session):
    """Create default and test users if not exist."""
    pw = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
    test_users = [
        ("admin", "admin"),
        ("manager", "manager"),
        ("designer", "designer"),
        ("constructor", "constructor"),
        ("cutter", "cutter"),
        ("tailor", "tailor"),
    ]
    for username, role_name in test_users:
        if session.query(User).filter_by(username=username).first():
            continue
        role = session.query(Role).filter_by(name=role_name).first()
        if role:
            session.add(User(username=username, password_hash=pw, role_id=role.id))
    session.commit()


def seed_expense_categories(session):
    """Create default expense categories."""
    categories = ["Аренда", "Материалы", "Коммунальные", "Зарплата", "Прочее"]
    for name in categories:
        if not session.query(ExpenseCategory).filter_by(name=name).first():
            session.add(ExpenseCategory(name=name))
    session.commit()


def seed_demo_data(session):
    """Add demo data (employees, clients, materials, orders) if DB is empty."""
    orders_count = session.query(Order).count()
    if orders_count >= 10:
        return  # Already has data

    # Employees
    employees_data = [
        ("Анна Петрова", "designer", 35000, 5, 500),
        ("Мария Сидорова", "constructor", 40000, 7, 600),
        ("Елена Козлова", "cutter", 30000, 4, 450),
        ("Ольга Новикова", "tailor", 32000, 6, 550),
        ("Ирина Морозова", "tailor", 28000, 5, 480),
        ("Светлана Волкова", "designer", 38000, 6, 520),
        ("Татьяна Соколова", "constructor", 42000, 8, 650),
    ]
    employees = []
    for name, pos, base, pct, hourly in employees_data:
        existing = session.query(Employee).filter(Employee.full_name == name).first()
        if not existing:
            emp = Employee(full_name=name, position=pos, base_salary=base,
                          order_percent=pct, hourly_rate=hourly,
                          phone=f"+7 9{random.randint(10,99)} {random.randint(100,999)}-{random.randint(10,99)}-{random.randint(10,99)}")
            session.add(emp)
            session.flush()
            employees.append(emp)
        else:
            employees.append(existing)
    if not employees:
        employees = list(session.query(Employee).all())

    # Clients
    clients_data = [
        ("Смирнова Татьяна", "+7 916 123-45-67"), ("Кузнецов Андрей", "+7 903 234-56-78"),
        ("Попова Екатерина", "+7 926 345-67-89"), ("Васильев Дмитрий", "+7 495 456-78-90"),
        ("Михайлова Анна", "+7 916 567-89-01"), ("Новиков Сергей", "+7 903 678-90-12"),
        ("Федорова Ольга", "+7 926 789-01-23"), ("Морозов Иван", "+7 916 890-12-34"),
        ("Козлова Елена", "+7 903 901-23-45"), ("Лебедева Мария", "+7 926 012-34-56"),
        ("Семёнов Алексей", "+7 495 123-45-67"), ("Егорова Наталья", "+7 916 234-56-78"),
        ("Павлова Ольга", "+7 903 345-67-89"), ("Соловьёв Петр", "+7 926 456-78-90"),
        ("Владимирова Ирина", "+7 495 567-89-01"),
    ]
    clients = []
    for name, phone in clients_data:
        existing = session.query(Client).filter(Client.full_name == name).first()
        if not existing:
            c = Client(full_name=name, phone=phone)
            session.add(c)
            session.flush()
            clients.append(c)
        else:
            clients.append(existing)
    if not clients:
        clients = list(session.query(Client).all())

    # Materials
    materials_data = [
        ("Шёлк атлас", "Ткань", "м", 1200, 50), ("Хлопок сатин", "Ткань", "м", 450, 100),
        ("Шерсть кашемир", "Ткань", "м", 2500, 30), ("Лён", "Ткань", "м", 600, 80),
        ("Молнии", "Фурнитура", "шт", 50, 200), ("Пуговицы", "Фурнитура", "уп", 120, 50),
        ("Нитки", "Прочее", "кат", 80, 100), ("Бархат", "Ткань", "м", 1800, 40),
        ("Джинса", "Ткань", "м", 550, 120), ("Подплечники", "Фурнитура", "шт", 80, 80),
    ]
    for name, cat, unit, price, qty in materials_data:
        if not session.query(Material).filter(Material.name == name).first():
            session.add(Material(name=name, category=cat, unit=unit, price_per_unit=price, quantity=qty))

    session.commit()

    # Orders (50+)
    statuses = ["accepted", "design", "construction", "cutting", "sewing", "ready"]
    today = date.today()
    orders_to_add = 55 - orders_count
    if orders_to_add <= 0 or not employees or not clients:
        return

    for i in range(orders_to_add):
        client = random.choice(clients)
        status = random.choices(statuses, weights=[1, 2, 2, 2, 2, 3])[0]
        deadline = today + timedelta(days=random.randint(5, 45))
        amount = random.randint(3000, 75000)
        descs = ["Платье вечернее", "Костюм", "Пальто", "Юбка", "Блузка", "Брюки", "Жакет", "Сарафан"]
        order = Order(
            client_id=client.id,
            status=status,
            total_amount=amount,
            description=f"{random.choice(descs)} — заказ #{orders_count + i + 1}",
            deadline=deadline,
            completed_at=datetime.utcnow() - timedelta(days=random.randint(0, 60)) if status == "ready" else None
        )
        session.add(order)
        session.flush()

        for stage in ["design", "construction", "cutting", "sewing"]:
            emp = random.choice(employees)
            session.add(OrderAssignment(order_id=order.id, employee_id=emp.id, stage=stage))

        if random.random() > 0.4:
            emp = random.choice(employees)
            session.add(WorkLog(employee_id=emp.id, order_id=order.id, hours=round(random.uniform(2, 10), 1),
                               date=today - timedelta(days=random.randint(0, 30))))

    # Expenses
    categories = list(session.query(ExpenseCategory).all())
    for _ in range(25):
        cat = random.choice(categories)
        exp_date = today - timedelta(days=random.randint(0, 90))
        session.add(Expense(category_id=cat.id, amount=random.randint(500, 35000),
                            date=exp_date, description=f"Расход: {cat.name}"))

    session.commit()


def run_init():
    """Run full initialization."""
    init_db()
    db = SessionLocal()
    try:
        seed_roles(db)
        seed_admin(db)
        seed_expense_categories(db)
        seed_demo_data(db)
    finally:
        db.close()
