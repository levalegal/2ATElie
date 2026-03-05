"""Application configuration."""
import os
import sys
from pathlib import Path

# Base paths - handle PyInstaller frozen exe
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "atelier.db"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Database URL
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Roles
ROLES = {
    "admin": "Админ",
    "manager": "Руководитель",
    "designer": "Дизайнер",
    "constructor": "Модельер-конструктор",
    "cutter": "Закройщик",
    "tailor": "Портной",
}

# Order statuses
ORDER_STATUSES = {
    "accepted": "Принят",
    "design": "Дизайн",
    "construction": "Конструирование",
    "cutting": "Раскрой",
    "sewing": "Пошив",
    "ready": "Готов",
}
