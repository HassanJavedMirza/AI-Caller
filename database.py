"""
database.py — SQLAlchemy engine + session factory.
All other modules import `get_db` from here.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

load_dotenv()

# ── Build connection URL ───────────────────────────────────────────────────
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "3306")
DB_USER     = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME     = os.getenv("DB_NAME", "ai_debt_reminder")

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ── Engine (pool_pre_ping keeps stale connections from crashing the app) ──
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,          # Set True to log all SQL — handy while debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Base class that all ORM models inherit from ────────────────────────────
class Base(DeclarativeBase):
    pass


# ── FastAPI dependency ─────────────────────────────────────────────────────
def get_db():
    """Yield a DB session; always close it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_connection() -> bool:
    """Utility called at startup to verify DB is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        print(f"[DB] Connection failed: {exc}")
        return False
