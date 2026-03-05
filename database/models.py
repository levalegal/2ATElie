"""SQLAlchemy models for atelier application."""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, ForeignKey, Text, Boolean, Enum
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Role(Base):
    """User roles."""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    users = relationship("User", back_populates="role")


class User(Base):
    """System users."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    role = relationship("Role", back_populates="users")
    employee = relationship("Employee", back_populates="user", uselist=False)


class Employee(Base):
    """Employees (linked to users)."""
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    full_name = Column(String(200), nullable=False)
    position = Column(String(100), nullable=False)  # designer, constructor, cutter, tailor
    base_salary = Column(Float, default=0)  # Fixed monthly rate
    order_percent = Column(Float, default=0)  # % from order
    hourly_rate = Column(Float, default=0)  # For hourly work
    phone = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="employee")
    work_logs = relationship("WorkLog", back_populates="employee")
    salary_records = relationship("SalaryRecord", back_populates="employee")
    order_assignments = relationship("OrderAssignment", back_populates="employee")


class Client(Base):
    """Clients."""
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(200), nullable=False)
    phone = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    address = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="client")


class Order(Base):
    """Orders."""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    status = Column(String(50), default="accepted")
    total_amount = Column(Float, default=0)
    description = Column(Text, nullable=True)
    accepted_at = Column(DateTime, default=datetime.utcnow)
    deadline = Column(Date, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = relationship("Client", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    materials = relationship("OrderMaterial", back_populates="order", cascade="all, delete-orphan")
    work_logs = relationship("WorkLog", back_populates="order")
    assignments = relationship("OrderAssignment", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    """Order items (garment positions)."""
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    name = Column(String(200), nullable=False)
    quantity = Column(Integer, default=1)
    price = Column(Float, default=0)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    notes = Column(Text, nullable=True)

    order = relationship("Order", back_populates="items")
    employee = relationship("Employee", backref="order_items")


class OrderAssignment(Base):
    """Assign employees to order stages."""
    __tablename__ = "order_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    stage = Column(String(50), nullable=False)  # design, construction, cutting, sewing
    assigned_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="assignments")
    employee = relationship("Employee", back_populates="order_assignments")


class Material(Base):
    """Materials (fabric, accessories)."""
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    category = Column(String(50), nullable=True)  # fabric, accessories, etc.
    unit = Column(String(20), default="м")
    price_per_unit = Column(Float, default=0)
    quantity = Column(Float, default=0)  # Stock
    created_at = Column(DateTime, default=datetime.utcnow)

    order_materials = relationship("OrderMaterial", back_populates="material")


class OrderMaterial(Base):
    """Materials used in orders."""
    __tablename__ = "order_materials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, default=0)

    order = relationship("Order", back_populates="materials")
    material = relationship("Material", back_populates="order_materials")


class WorkLog(Base):
    """Work time logs for salary calculation."""
    __tablename__ = "work_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    hours = Column(Float, nullable=False)
    date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="work_logs")
    order = relationship("Order", back_populates="work_logs")


class ExpenseCategory(Base):
    """Expense categories."""
    __tablename__ = "expense_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    expenses = relationship("Expense", back_populates="category")


class Expense(Base):
    """Expenses."""
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("expense_categories.id"), nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(Date, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("ExpenseCategory", back_populates="expenses")


class SalaryRecord(Base):
    """Salary records."""
    __tablename__ = "salary_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    base_amount = Column(Float, default=0)
    order_amount = Column(Float, default=0)  # From % of orders
    hourly_amount = Column(Float, default=0)
    bonus = Column(Float, default=0)
    total = Column(Float, nullable=False)
    paid = Column(Boolean, default=False)
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="salary_records")
