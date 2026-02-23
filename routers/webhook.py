"""
routers/webhook.py — Vapi webhook endpoint.
After every call ends, Vapi sends a POST request here with the full
call result: status, transcript, recording URL, duration, and summary.
We save it all to the calls table and update the invoice status.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session

from database import SessionLocal
import models

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["Webhook"])


@router.post("/vapi")
async def vapi_webhook(request: Request):
    """
    Receives call result from Vapi after each call ends.
    Vapi sends this automatically to your webhook URL.

    Set your webhook URL in Vapi dashboard:
    Assistants → Your Assistant → Server URL → https://yourdomain.com/webhook/vapi
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Vapi sends a 'message' object with a 'type' field
    message      = payload.get("message", {})
    message_type = message.get("type", "")

    logger.info(f"[Webhook] Received Vapi event: {message_type}")

    # ── We only care about end-of-call reports ─────────────────────────────
    if message_type != "end-of-call-report":
        return {"status": "ignored", "type": message_type}

    db: Session = SessionLocal()
    try:
        # ── Extract call data from Vapi payload ────────────────────────────
        call_data        = message.get("call", {})
        provider_call_id = call_data.get("id")
        call_status      = message.get("endedReason", "unknown")
        duration_seconds = int(message.get("durationSeconds", 0))
        recording_url    = message.get("recordingUrl")
        transcript       = message.get("transcript")
        summary          = message.get("summary")

        # ── Map Vapi end reasons to our status labels ──────────────────────
        status_map = {
            "customer-ended-call":    "completed",
            "assistant-ended-call":   "completed",
            "voicemail":              "no-answer",
            "no-answer":              "no-answer",
            "busy":                   "busy",
            "failed":                 "failed",
            "customer-did-not-answer":"no-answer",
        }
        mapped_status = status_map.get(call_status, call_status)

        if not provider_call_id:
            logger.warning("[Webhook] No call ID in payload — cannot update record")
            return {"status": "skipped", "reason": "no call id"}

        # ── Find the existing call log by provider_call_id ─────────────────
        call_log = db.query(models.Call).filter(
            models.Call.provider_call_id == provider_call_id
        ).first()

        if call_log:
            # Update existing log
            call_log.call_status      = mapped_status
            call_log.duration_seconds = duration_seconds
            call_log.recording_url    = recording_url
            call_log.transcript       = transcript
            call_log.ai_summary       = summary
            logger.info(f"[Webhook] ✅ Updated call log for Vapi call {provider_call_id}")
        else:
            # Create new log if not found (edge case)
            call_log = models.Call(
                provider_call_id = provider_call_id,
                call_status      = mapped_status,
                duration_seconds = duration_seconds,
                recording_url    = recording_url,
                transcript       = transcript,
                ai_summary       = summary,
            )
            db.add(call_log)
            logger.info(f"[Webhook] ✅ Created new call log for Vapi call {provider_call_id}")

        db.commit()

        # ── Update invoice status based on call outcome ────────────────────
        if call_log.invoice_id:
            invoice = db.query(models.Invoice).filter(
                models.Invoice.invoice_id == call_log.invoice_id
            ).first()

            if invoice:
                if mapped_status == "completed":
                    # Keep as overdue — human review needed to confirm payment
                    # Admin can manually mark as paid from dashboard
                    pass
                elif mapped_status in ("no-answer", "busy", "failed"):
                    # Put back to overdue so scheduler can retry
                    invoice.status = "overdue"
                    db.commit()

        # ── SMS fallback if no answer ──────────────────────────────────────
        if mapped_status == "no-answer" and call_log.invoice_id:
            _send_sms_fallback(db, call_log.invoice_id)

        return {"status": "ok"}

    except Exception as exc:
        logger.exception(f"[Webhook] Error processing Vapi webhook: {exc}")
        return {"status": "error", "detail": str(exc)}
    finally:
        db.close()


def _send_sms_fallback(db: Session, invoice_id: int):
    """Send SMS when client didn't answer the call."""
    try:
        from vapi_service import send_sms, is_vapi_configured
        if not is_vapi_configured():
            return

        invoice = db.query(models.Invoice).filter(
            models.Invoice.invoice_id == invoice_id
        ).first()
        if not invoice:
            return

        client = db.query(models.Client).filter(
            models.Client.client_id == invoice.client_id
        ).first()
        if not client:
            return

        sms_message = (
            f"Hello {client.full_name}, we tried to reach you regarding "
            f"invoice #{invoice_id} for {invoice.currency} {float(invoice.amount):,.2f} "
            f"which was due on {invoice.due_date}. "
            f"Please contact us to arrange payment. Thank you."
        )
        result = send_sms(client.phone_number, sms_message)
        logger.info(f"[Webhook] SMS fallback {'✅ sent' if result['success'] else '❌ failed'} to {client.phone_number}")

    except Exception as exc:
        logger.exception(f"[Webhook] SMS fallback error: {exc}")