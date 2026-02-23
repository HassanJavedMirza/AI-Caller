"""
vapi_service.py — Handles all communication with the Vapi API.
This file is ready to go — just add your credentials to .env when you
have a paid number and it will start making real calls automatically.
"""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

VAPI_API_KEY          = os.getenv("VAPI_API_KEY", "")
VAPI_PHONE_NUMBER_ID  = os.getenv("VAPI_PHONE_NUMBER_ID", "")
VAPI_ASSISTANT_ID     = os.getenv("VAPI_ASSISTANT_ID", "")
VAPI_BASE_URL         = "https://api.vapi.ai"


def is_vapi_configured() -> bool:
    """Check if all Vapi credentials are present in .env"""
    return all([VAPI_API_KEY, VAPI_PHONE_NUMBER_ID, VAPI_ASSISTANT_ID])


def make_call(
    customer_phone: str,
    customer_name:  str,
    invoice_id:     int,
    amount:         float,
    currency:       str,
    due_date:       str,
) -> dict:
    """
    Initiate a real phone call via Vapi.

    Returns dict with:
      - success: bool
      - call_id: str (Vapi's call ID, save to calls table)
      - error: str (if success is False)

    NOTE: This function will return success=False with a clear message
    if Vapi credentials are not configured yet.
    """

    # ── Guard: no credentials yet ─────────────────────────────────────────
    if not is_vapi_configured():
        return {
            "success": False,
            "call_id": None,
            "error":   "Vapi not configured. Add VAPI_API_KEY, VAPI_PHONE_NUMBER_ID, and VAPI_ASSISTANT_ID to your .env file.",
        }

    # ── Build the call payload ─────────────────────────────────────────────
    payload = {
        "phoneNumberId": VAPI_PHONE_NUMBER_ID,
        "assistantId":   VAPI_ASSISTANT_ID,
        "customer": {
            "number": customer_phone,
            "name":   customer_name,
        },
        # Pass invoice details as assistant overrides so the AI knows
        # exactly who it's calling and how much they owe
        "assistantOverrides": {
            "variableValues": {
                "customer_name": customer_name,
                "invoice_id":    str(invoice_id),
                "amount":        f"{amount:,.2f}",
                "currency":      currency,
                "due_date":      due_date,
            }
        },
    }

    # ── Make the API call ──────────────────────────────────────────────────
    try:
        response = httpx.post(
            f"{VAPI_BASE_URL}/call/phone",
            headers={
                "Authorization": f"Bearer {VAPI_API_KEY}",
                "Content-Type":  "application/json",
            },
            json=payload,
            timeout=30,
        )

        if response.status_code in (200, 201):
            data = response.json()
            return {
                "success": True,
                "call_id": data.get("id"),
                "error":   None,
            }
        else:
            return {
                "success": False,
                "call_id": None,
                "error":   f"Vapi API error {response.status_code}: {response.text}",
            }

    except Exception as exc:
        return {
            "success": False,
            "call_id": None,
            "error":   f"Network error calling Vapi: {str(exc)}",
        }


def send_sms(phone_number: str, message: str) -> dict:
    """
    Send an SMS fallback when a call gets no answer.
    Vapi supports SMS — will be wired up once you have a paid number.
    """
    if not is_vapi_configured():
        return {
            "success": False,
            "error":   "Vapi not configured. Cannot send SMS.",
        }

    try:
        response = httpx.post(
            f"{VAPI_BASE_URL}/message",
            headers={
                "Authorization": f"Bearer {VAPI_API_KEY}",
                "Content-Type":  "application/json",
            },
            json={
                "phoneNumberId": VAPI_PHONE_NUMBER_ID,
                "customer":      {"number": phone_number},
                "message":       message,
            },
            timeout=15,
        )
        return {"success": response.status_code in (200, 201)}
    except Exception as exc:
        return {"success": False, "error": str(exc)}