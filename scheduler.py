"""
scheduler.py — Background scheduler using APScheduler.
Reads call_time and active_days from scheduler_settings table,
finds overdue invoices, and triggers Vapi calls for each one.
"""

import logging
from datetime import datetime, date

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from database import SessionLocal
import models
from vapi_service import make_call, send_sms, is_vapi_configured

logger = logging.getLogger(__name__)

# Single global scheduler instance
scheduler = BackgroundScheduler(timezone="UTC")


# ── Core job ──────────────────────────────────────────────────────────────

def run_debt_calls():
    """
    Main job — called by the scheduler at the configured time.
    1. Loads settings from DB
    2. Checks if today is an active day
    3. Finds all overdue invoices that haven't exceeded max retries
    4. Calls each client via Vapi
    5. Saves call log to DB
    6. If no answer → sends SMS
    """
    db: Session = SessionLocal()
    logger.info(f"[Scheduler] Job triggered at {datetime.utcnow()}")

    try:
        # ── Load settings ──────────────────────────────────────────────────
        settings = db.query(models.SchedulerSettings).filter(
            models.SchedulerSettings.id == 1
        ).first()

        if not settings or not settings.is_active:
            logger.info("[Scheduler] Scheduler is disabled. Skipping.")
            return

        # ── Check if today is an active day ───────────────────────────────
        today_name = datetime.utcnow().strftime("%a")  # e.g. "Mon"
        if today_name not in (settings.active_days or []):
            logger.info(f"[Scheduler] Today is {today_name}, not in active days {settings.active_days}. Skipping.")
            return

        # ── Check Vapi credentials ────────────────────────────────────────
        if not is_vapi_configured():
            logger.warning("[Scheduler] Vapi credentials not configured. Skipping calls. Add VAPI_API_KEY, VAPI_PHONE_NUMBER_ID, VAPI_ASSISTANT_ID to .env")
            return

        # ── Mark overdue invoices ──────────────────────────────────────────
        today = date.today()
        db.query(models.Invoice).filter(
            models.Invoice.status == "unpaid",
            models.Invoice.due_date < today,
        ).update({"status": "overdue"}, synchronize_session=False)
        db.commit()

        # ── Find overdue invoices to call ──────────────────────────────────
        # Only call invoices where retry count < max_retries
        overdue_invoices = (
            db.query(models.Invoice)
            .filter(models.Invoice.status == "overdue")
            .all()
        )

        if not overdue_invoices:
            logger.info("[Scheduler] No overdue invoices found. Nothing to do.")
            return

        logger.info(f"[Scheduler] Found {len(overdue_invoices)} overdue invoices. Starting calls...")

        for invoice in overdue_invoices:
            # Check how many call attempts already made for this invoice
            attempts = db.query(models.Call).filter(
                models.Call.invoice_id == invoice.invoice_id
            ).count()

            if attempts >= settings.max_retries:
                logger.info(f"[Scheduler] Invoice #{invoice.invoice_id} already has {attempts} attempts. Skipping.")
                continue

            # Get client info
            client = db.query(models.Client).filter(
                models.Client.client_id == invoice.client_id
            ).first()

            if not client:
                logger.warning(f"[Scheduler] No client found for invoice #{invoice.invoice_id}. Skipping.")
                continue

            logger.info(f"[Scheduler] Calling {client.full_name} ({client.phone_number}) for invoice #{invoice.invoice_id}")

            # ── Make the call ──────────────────────────────────────────────
            result = make_call(
                customer_phone = client.phone_number,
                customer_name  = client.full_name,
                invoice_id     = invoice.invoice_id,
                amount         = float(invoice.amount),
                currency       = invoice.currency,
                due_date       = str(invoice.due_date),
            )

            # ── Save call log immediately ──────────────────────────────────
            call_log = models.Call(
                invoice_id       = invoice.invoice_id,
                provider_call_id = result.get("call_id"),
                call_status      = "initiated" if result["success"] else "failed",
                ai_summary       = result.get("error") if not result["success"] else "Call initiated successfully",
            )
            db.add(call_log)

            # Update last reminder sent on invoice
            invoice.last_reminder_sent = datetime.utcnow()
            invoice.status = "processing"
            db.commit()

            if result["success"]:
                logger.info(f"[Scheduler] ✅ Call initiated for invoice #{invoice.invoice_id} — Vapi call ID: {result['call_id']}")
            else:
                logger.error(f"[Scheduler] ❌ Call failed for invoice #{invoice.invoice_id} — {result['error']}")

                # SMS fallback on failure
                sms_message = (
                    f"Hello {client.full_name}, this is a reminder that your invoice "
                    f"#{invoice.invoice_id} for {invoice.currency} {float(invoice.amount):,.2f} "
                    f"was due on {invoice.due_date}. Please contact us to arrange payment."
                )
                sms_result = send_sms(client.phone_number, sms_message)
                logger.info(f"[Scheduler] SMS fallback: {'✅ sent' if sms_result['success'] else '❌ failed'}")

    except Exception as exc:
        logger.exception(f"[Scheduler] Unexpected error: {exc}")
    finally:
        db.close()


# ── Scheduler management ──────────────────────────────────────────────────

def _get_settings_from_db():
    """Fetch current scheduler settings from DB."""
    db = SessionLocal()
    try:
        return db.query(models.SchedulerSettings).filter(
            models.SchedulerSettings.id == 1
        ).first()
    finally:
        db.close()


def start_scheduler():
    """
    Start the scheduler with settings loaded from DB.
    Called once at app startup in main.py lifespan.
    """
    settings = _get_settings_from_db()

    call_time = "09:00"
    if settings and settings.call_time:
        call_time = settings.call_time

    hour, minute = call_time.split(":")

    scheduler.add_job(
        run_debt_calls,
        trigger   = CronTrigger(hour=int(hour), minute=int(minute), timezone="UTC"),
        id        = "debt_calls",
        name      = "Daily Debt Call Job",
        replace_existing = True,
    )

    scheduler.start()
    logger.info(f"[Scheduler] ✅ Started — will run daily at {call_time} UTC")


def restart_scheduler_with_new_settings():
    """
    Called by the /settings PATCH endpoint after admin updates schedule.
    Reschedules the job with the new time without restarting the app.
    """
    settings = _get_settings_from_db()
    if not settings:
        return

    hour, minute = settings.call_time.split(":")

    scheduler.reschedule_job(
        "debt_calls",
        trigger = CronTrigger(hour=int(hour), minute=int(minute), timezone="UTC"),
    )
    logger.info(f"[Scheduler] 🔄 Rescheduled to run at {settings.call_time} UTC")


def stop_scheduler():
    """Called at app shutdown."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("[Scheduler] 🛑 Stopped")