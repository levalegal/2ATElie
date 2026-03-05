"""Authentication service."""
import bcrypt
from sqlalchemy.orm import Session

from database.models import User, Role


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def authenticate(session: Session, username: str, password: str) -> User | None:
    """Authenticate user. Returns User if successful, None otherwise."""
    user = session.query(User).filter(
        User.username == username,
        User.is_active == True
    ).first()
    if user and verify_password(password, user.password_hash):
        return user
    return None


def get_user_role(session: Session, user: User) -> Role:
    """Get user's role."""
    return session.query(Role).filter(Role.id == user.role_id).first()
