"""Creates the default admin account from ADMIN_EMAIL / ADMIN_PASSWORD in .env."""
import os
from sqlalchemy import select
from sqlalchemy.orm import Session
from app import config  # loads .env
from app.auth import hash_password
from app.database import engine
from app.models import User, Role


def seed_admin(email=None, password=None):
    email = (email or os.getenv("ADMIN_EMAIL", "admin@example.com")).lower()
    password = password or os.getenv("ADMIN_PASSWORD", "Admin@12345")
    with Session(engine) as db:
        role = db.scalar(select(Role).where(Role.name == "admin"))
        if role is None:
            raise SystemExit("Run init_db.py first.")
        if db.scalar(select(User).where(User.email == email)):
            return f"Admin {email} already exists."
        db.add(User(name="Administrator", email=email, password_hash=hash_password(password), role_id=role.id))
        db.commit()
        return f"Admin created: {email}"


if __name__ == "__main__":
    print(seed_admin())
