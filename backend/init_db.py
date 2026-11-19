"""Creates extension, tables, roles, stored functions and indexes. Safe to re-run."""
import os
from sqlalchemy import text, select
from sqlalchemy.orm import Session
from app.database import engine, Base
from app import models  # noqa: F401
from app.models import Role

SQL_DIR = os.path.join(os.path.dirname(__file__), "..", "db")


def run_sql_file(conn, name):
    with open(os.path.join(SQL_DIR, name), encoding="utf-8") as f:
        conn.exec_driver_sql(f.read().replace("%", "%%"))


def init_db():
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        run_sql_file(conn, "functions.sql")
        run_sql_file(conn, "indexes.sql")
    with Session(engine) as db:
        for name in ("admin", "user"):
            if not db.scalar(select(Role).where(Role.name == name)):
                db.add(Role(name=name))
        db.commit()


if __name__ == "__main__":
    init_db()
    print("Database initialized.")
