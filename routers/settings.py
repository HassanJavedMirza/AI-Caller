import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas  import SettingsOut, SettingsUpdate
import models
import auth_utils

router = APIRouter(prefix="/settings", tags=["Settings"])

DEFAULT_SETTINGS = {
    "id":                   1,
    "call_time":            "09:00",
    "active_days":          ["Mon", "Tue", "Wed", "Thu", "Fri"],
    "is_active":            True,
    "max_retries":          3,
    "retry_interval_hours": 24,
}


def _get_or_create_settings(db: Session) -> models.SchedulerSettings:
    settings = db.query(models.SchedulerSettings).filter(
        models.SchedulerSettings.id == 1
    ).first()
    if not settings:
        settings = models.SchedulerSettings(**DEFAULT_SETTINGS)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("/", response_model=SettingsOut)
def get_settings(
    db: Session = Depends(get_db),
    _:  models.Admin = Depends(auth_utils.get_current_admin),
):
    return _get_or_create_settings(db)


@router.patch("/", response_model=SettingsOut)
def update_settings(
    payload: SettingsUpdate,
    db:      Session = Depends(get_db),
    _:       models.Admin = Depends(auth_utils.get_current_admin),
):
    settings = _get_or_create_settings(db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(settings)

    # Restart scheduler with new time settings
    try:
        from scheduler import restart_scheduler_with_new_settings
        restart_scheduler_with_new_settings()
    except Exception as e:
        pass  # Don't fail the request if scheduler reschedule fails

    return settings


@router.get("/vapi-status", tags=["Settings"])
def vapi_status():
    """Check if Vapi credentials are configured — used by the frontend notice."""
    from vapi_service import is_vapi_configured, VAPI_API_KEY, VAPI_PHONE_NUMBER_ID, VAPI_ASSISTANT_ID
    return {
        "configured":        is_vapi_configured(),
        "has_api_key":       bool(VAPI_API_KEY),
        "has_phone_number":  bool(VAPI_PHONE_NUMBER_ID),
        "has_assistant_id":  bool(VAPI_ASSISTANT_ID),
        "message":           "Vapi is ready" if is_vapi_configured() else "Add VAPI_API_KEY, VAPI_PHONE_NUMBER_ID, VAPI_ASSISTANT_ID to your .env file to enable AI calling",
    }