"""
schemas.py — Pydantic v2 models for request validation and response serialization.
Every router uses these — never return raw ORM objects to the client.
"""

from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, EmailStr, field_validator


# ══════════════════════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"


# ══════════════════════════════════════════════════════════════════════
#  ADMIN
# ══════════════════════════════════════════════════════════════════════

class AdminCreate(BaseModel):
    username: str
    email:    EmailStr
    password: str


class AdminOut(BaseModel):
    admin_id:   int
    username:   str
    email:      str
    created_at: datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════
#  CLIENT
# ══════════════════════════════════════════════════════════════════════

class ClientCreate(BaseModel):
    full_name:    str
    phone_number: str
    email:        Optional[EmailStr] = None
    timezone:     str = "UTC"
    extra_data:   Optional[Dict[str, Any]] = None


class ClientUpdate(BaseModel):
    full_name:    Optional[str]       = None
    phone_number: Optional[str]       = None
    email:        Optional[EmailStr]  = None
    timezone:     Optional[str]       = None
    extra_data:   Optional[Dict[str, Any]] = None


class ClientOut(BaseModel):
    client_id:    int
    full_name:    str
    phone_number: str
    email:        Optional[str]
    timezone:     str
    extra_data:   Optional[Dict[str, Any]]
    created_at:   datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════
#  INVOICE
# ══════════════════════════════════════════════════════════════════════

InvoiceStatus = Literal["unpaid", "paid", "overdue", "processing"]


class InvoiceCreate(BaseModel):
    client_id: int
    amount:    Decimal
    currency:  str = "USD"
    due_date:  date
    status:    InvoiceStatus = "unpaid"


class InvoiceUpdate(BaseModel):
    amount:   Optional[Decimal]        = None
    currency: Optional[str]            = None
    due_date: Optional[date]           = None
    status:   Optional[InvoiceStatus]  = None


class InvoiceOut(BaseModel):
    invoice_id:         int
    client_id:          int
    amount:             Decimal
    currency:           str
    due_date:           date
    status:             str
    last_reminder_sent: Optional[datetime]

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════
#  CALL
# ══════════════════════════════════════════════════════════════════════

class CallCreate(BaseModel):
    invoice_id:       int
    provider_call_id: Optional[str] = None
    call_status:      Optional[str] = None
    duration_seconds: Optional[int] = None
    recording_url:    Optional[str] = None
    transcript:       Optional[str] = None
    ai_summary:       Optional[str] = None


class CallOut(BaseModel):
    call_id:          int
    invoice_id:       int
    provider_call_id: Optional[str]
    call_status:      Optional[str]
    duration_seconds: Optional[int]
    recording_url:    Optional[str]
    transcript:       Optional[str]
    ai_summary:       Optional[str]
    created_at:       datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════
#  SCHEDULER SETTINGS
# ══════════════════════════════════════════════════════════════════════

class SettingsUpdate(BaseModel):
    call_time:            Optional[str]       = None   # "HH:MM"
    active_days:          Optional[List[str]] = None   # ["Mon","Tue",...]
    is_active:            Optional[bool]      = None
    max_retries:          Optional[int]       = None
    retry_interval_hours: Optional[int]       = None

    @field_validator("call_time")
    @classmethod
    def validate_time_format(cls, v):
        if v is not None:
            parts = v.split(":")
            if len(parts) != 2 or not all(p.isdigit() for p in parts):
                raise ValueError("call_time must be HH:MM format")
            h, m = int(parts[0]), int(parts[1])
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError("Invalid time value")
        return v


class SettingsOut(BaseModel):
    id:                   int
    call_time:            str
    active_days:          List[str]
    is_active:            bool
    max_retries:          int
    retry_interval_hours: int
    updated_at:           Optional[datetime]

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════════════════
#  BULK UPLOAD RESPONSE
# ══════════════════════════════════════════════════════════════════════

class BulkUploadResult(BaseModel):
    inserted: int
    skipped:  int
    errors:   List[str]
