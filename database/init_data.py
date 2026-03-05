"""Initialize database with default data."""
import bcrypt
from database.session import SessionLocal, init_db
from database.models import Role, User, ExpenseCategory


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
    """Create admin user if not exists."""
    if session.query(User).filter_by(username="admin").first():
        return
    admin_role = session.query(Role).filter_by(name="admin").first()
    if admin_role:
        password_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
        session.add(User(username="admin", password_hash=password_hash, role_id=admin_role.id))
        session.commit()


def seed_expense_categories(session):
    """Create default expense categories."""
    categories = ["Аренда", "Материалы", "Коммунальные", "Зарплата", "Прочее"]
    for name in categories:
        if not session.query(ExpenseCategory).filter_by(name=name).first():
            session.add(ExpenseCategory(name=name))
    session.commit()


def run_init():
    """Run full initialization."""
    init_db()
    db = SessionLocal()
    try:
        seed_roles(db)
        seed_admin(db)
        seed_expense_categories(db)
    finally:
        db.close()
