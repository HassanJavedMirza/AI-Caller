import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from schemas  import CallCreate, CallOut
import models
import auth_utils

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/calls", tags=["Calls"])


@router.get("/", response_model=list[CallOut])
def list_calls(
    skip:       int = Query(0,   ge=0),
    limit:      int = Query(100, ge=1, le=500),
    invoice_id: int = Query(None),
    status:     str = Query(None),
    db:         Session = Depends(get_db),
    _:          models.Admin = Depends(auth_utils.get_current_admin),
):
    q = db.query(models.Call).order_by(models.Call.created_at.desc())
    if invoice_id:
        q = q.filter(models.Call.invoice_id == invoice_id)
    if status:
        q = q.filter(models.Call.call_status == status)
    return q.offset(skip).limit(limit).all()


@router.get("/{call_id}", response_model=CallOut)
def get_call(
    call_id: int,
    db:      Session = Depends(get_db),
    _:       models.Admin = Depends(auth_utils.get_current_admin),
):
    call = db.query(models.Call).filter(models.Call.call_id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call log not found")
    return call


@router.get("/{call_id}/transcript")
def get_transcript(
    call_id: int,
    db:      Session = Depends(get_db),
    _:       models.Admin = Depends(auth_utils.get_current_admin),
):
    call = db.query(models.Call).filter(models.Call.call_id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call log not found")
    return {
        "call_id":          call.call_id,
        "invoice_id":       call.invoice_id,
        "call_status":      call.call_status,
        "duration_seconds": call.duration_seconds,
        "recording_url":    call.recording_url,
        "transcript":       call.transcript,
        "ai_summary":       call.ai_summary,
        "created_at":       call.created_at,
    }


# ── TRIGGER A REAL CALL ───────────────────────────────────────────────────

@router.post("/trigger/{invoice_id}")
def trigger_call(
    invoice_id: int,
    db:         Session = Depends(get_db),
    _:          models.Admin = Depends(auth_utils.get_current_admin),
):
    """
    Manually trigger an AI call for a specific invoice.
    Use this to test calls without waiting for the scheduler.
    """
    from vapi_service import make_call, is_vapi_configured

    # Check Vapi is configured
    if not is_vapi_configured():
        raise HTTPException(
            status_code=400,
            detail="Vapi is not configured. Add VAPI_API_KEY and VAPI_PHONE_NUMBER_ID to .env"
        )

    # Get invoice
    invoice = db.query(models.Invoice).filter(
        models.Invoice.invoice_id == invoice_id
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Get client
    client = db.query(models.Client).filter(
        models.Client.client_id == invoice.client_id
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found for this invoice")

    logger.info(f"[Manual Call] Triggering call for invoice #{invoice_id} — {client.full_name} ({client.phone_number})")

    # Trigger the call
    result = make_call(
        customer_phone = client.phone_number,
        customer_name  = client.full_name,
        invoice_id     = invoice.invoice_id,
        amount         = float(invoice.amount),
        currency       = invoice.currency,
        due_date       = str(invoice.due_date),
    )

    # Save call log
    call_log = models.Call(
        invoice_id       = invoice.invoice_id,
        provider_call_id = result.get("call_id"),
        call_status      = "initiated" if result["success"] else "failed",
        ai_summary       = result.get("error") if not result["success"] else "Call initiated manually by admin",
    )
    db.add(call_log)

    # Update invoice status
    if result["success"]:
        invoice.status             = "processing"
        invoice.last_reminder_sent = datetime.utcnow()

    db.commit()
    db.refresh(call_log)

    if result["success"]:
        logger.info(f"[Manual Call] ✅ Call initiated — Vapi ID: {result['call_id']}")
        return {
            "success":    True,
            "message":    f"Call initiated to {client.full_name} at {client.phone_number}",
            "call_id":    call_log.call_id,
            "vapi_call_id": result["call_id"],
        }
    else:
        logger.error(f"[Manual Call] ❌ Failed — {result['error']}")
        raise HTTPException(status_code=500, detail=result["error"])


@router.post("/", response_model=CallOut, status_code=201)
def create_call_log(
    payload: CallCreate,
    db:      Session = Depends(get_db),
    _:       models.Admin = Depends(auth_utils.get_current_admin),
):
    if not db.query(models.Invoice).filter(models.Invoice.invoice_id == payload.invoice_id).first():
        raise HTTPException(status_code=404, detail="Invoice not found")
    call = models.Call(**payload.model_dump())
    db.add(call)
    db.commit()
    db.refresh(call)
    return call


@router.delete("/{call_id}", status_code=204)
def delete_call(
    call_id: int,
    db:      Session = Depends(get_db),
    _:       models.Admin = Depends(auth_utils.get_current_admin),
):
    call = db.query(models.Call).filter(models.Call.call_id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call log not found")
    db.delete(call)
    db.commit()