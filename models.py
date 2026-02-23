"""
models.py — SQLAlchemy ORM models.
These map 1-to-1 with the MySQL tables you already created.
We also add the scheduler_settings table here (new).
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime,
    DECIMAL, Date, Enum, JSON, ForeignKey, Boolean, Time,
)
from sqlalchemy.orm import relationship
from database import Base


class Admin(Base):
    __tablename__ = "admins"

    admin_id      = Column(Integer, primary_key=True, autoincrement=True)
    username      = Column(String(50),  nullable=False, unique=True)
    email         = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)


class Client(Base):
    __tablename__ = "clients"

    client_id    = Column(Integer, primary_key=True, autoincrement=True)
    full_name    = Column(String(100), nullable=False)
    phone_number = Column(String(20),  nullable=False)
    email        = Column(String(100))
    timezone     = Column(String(50),  default="UTC")
    extra_data   = Column(JSON)
    created_at   = Column(DateTime, default=datetime.utcnow)

    invoices = relationship("Invoice", back_populates="client", cascade="all, delete")


class Invoice(Base):
    __tablename__ = "invoices"

    invoice_id        = Column(Integer, primary_key=True, autoincrement=True)
    client_id         = Column(Integer, ForeignKey("clients.client_id", ondelete="CASCADE"), nullable=False)
    amount            = Column(DECIMAL(15, 2), nullable=False)
    currency          = Column(String(3), default="USD")
    due_date          = Column(Date, nullable=False)
    status            = Column(
        Enum("unpaid", "paid", "overdue", "processing"),
        default="unpaid"
    )
    last_reminder_sent = Column(DateTime, nullable=True)

    client = relationship("Client", back_populates="invoices")
    calls  = relationship("Call",   back_populates="invoice", cascade="all, delete")


class Call(Base):
    __tablename__ = "calls"

    call_id          = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id       = Column(Integer, ForeignKey("invoices.invoice_id", ondelete="CASCADE"), nullable=False)
    provider_call_id = Column(String(100))
    call_status      = Column(String(20))
    duration_seconds = Column(Integer)
    recording_url    = Column(Text)
    transcript       = Column(Text)          # LONGTEXT equivalent
    ai_summary       = Column(Text)
    created_at       = Column(DateTime, default=datetime.utcnow)

    invoice = relationship("Invoice", back_populates="calls")


class SchedulerSettings(Base):
    """
    Stores the admin-configurable scheduler config.
    Only ONE row should ever exist (id=1).
    Use the /settings endpoints to read and update it.
    """
    __tablename__ = "scheduler_settings"

    id              = Column(Integer, primary_key=True, default=1)
    call_time       = Column(String(5),  default="09:00")   # "HH:MM" 24h format
    active_days     = Column(JSON,       default=["Mon", "Tue", "Wed", "Thu", "Fri"])
    is_active       = Column(Boolean,    default=True)
    max_retries     = Column(Integer,    default=3)          # call attempts before giving up
    retry_interval_hours = Column(Integer, default=24)       # hours between retries
    updated_at      = Column(DateTime,   default=datetime.utcnow, onupdate=datetime.utcnow)
