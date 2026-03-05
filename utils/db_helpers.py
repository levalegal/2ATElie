"""Database helpers with error handling."""
from contextlib import contextmanager

from database.session import get_db
from utils.logger import log


@contextmanager
def safe_db_operation(operation_name: str = "DB operation"):
    """Context manager for DB operations with error handling."""
    try:
        with get_db() as db:
            yield db
    except Exception as e:
        log.error("%s failed: %s", operation_name, str(e))
        raise
