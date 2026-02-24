"""
VAAPI
vapi_service.py — AI calling via official Vapi Python SDK.
System prompt is defined HERE in code — no need to manage it in Vapi dashboard.
Just add credentials to .env and calls will work automatically.
"""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

VAPI_API_KEY         = os.getenv("VAPI_API_KEY", "")
VAPI_PHONE_NUMBER_ID = os.getenv("VAPI_PHONE_NUMBER_ID", "")


def is_vapi_configured() -> bool:
    return bool(VAPI_API_KEY and VAPI_PHONE_NUMBER_ID)


def _build_system_prompt(customer_name, invoice_id, amount, currency, due_date):
    return f"""You are a professional and empathetic payment reminder agent calling on behalf of a business.

You are calling {customer_name} about invoice #{invoice_id} for {currency} {amount} which was due on {due_date}.

YOUR GOALS:
1. Confirm you are speaking with the right person
2. Inform them politely about the outstanding invoice
3. Get a clear commitment — payment date, payment plan, or reason for non-payment
4. If they say they already paid, ask for a transaction reference and note it
5. If they dispute the amount, note the dispute and say accounts team will review
6. If they request a payment plan, note the arrangement and say team will confirm
7. End the call professionally after reaching an outcome

STRICT RULES:
- You must ONLY discuss matters related to invoice #{invoice_id} and payment
- If asked ANYTHING off-topic (science, news, weather, general knowledge), respond:
  "I am only able to assist with matters related to your outstanding invoice today. Shall we get that sorted?"
- Never be rude, aggressive, or threatening under any circumstances
- Never discuss other clients or internal business details
- Never make promises about discounts or write-offs — only accounts team can do that
- Always stay calm even if the client becomes frustrated

VOICE STYLE:
- Speak naturally and conversationally — not like a robot reading a script
- Use the client's first name occasionally to keep it personal
- Keep responses concise — don't over-explain
- Pause and listen — let the client speak fully before responding"""


def make_call(customer_phone, customer_name, invoice_id, amount, currency, due_date):
    """
    Initiate a real phone call via Vapi Python SDK.
    Returns: { success, call_id, error }
    """
    if not is_vapi_configured():
        return {
            "success": False,
            "call_id": None,
            "error":   "Vapi not configured. Add VAPI_API_KEY and VAPI_PHONE_NUMBER_ID to .env",
        }

    try:
        from vapi import Vapi

        vapi_client   = Vapi(api_key=VAPI_API_KEY)
        amount_str    = f"{amount:,.2f}"
        system_prompt = _build_system_prompt(customer_name, invoice_id, amount_str, currency, due_date)

        response = vapi_client.calls.create(
            phone_number_id = VAPI_PHONE_NUMBER_ID,
            customer = {
                "number": customer_phone,
                "name":   customer_name,
            },
            assistant = {
                "name":         "DebtCall Agent",
                "firstMessage": f"Hello, may I speak with {customer_name} please?",
                "model": {
                    "provider":    "openai",
                    "model":       "gpt-4o",
                    "messages":    [{"role": "system", "content": system_prompt}],
                    "temperature": 0.4,
                },
                "voice": {
                    "provider": "11labs",
                    "voiceId":  "21m00Tcm4TlvDq8ikWAM",  # Rachel — most human sounding
                },
                "endCallPhrases": [
                    "goodbye", "bye", "thank you goodbye",
                    "have a good day", "that is all", "we are done"
                ],
            },
        )

        return {
            "success": True,
            "call_id": response.id,
            "error":   None,
        }

    except Exception as exc:
        return {
            "success": False,
            "call_id": None,
            "error":   f"Vapi call failed: {str(exc)}",
        }


def send_sms(phone_number, message):
    """Send SMS fallback when call gets no answer."""
    if not is_vapi_configured():
        return {"success": False, "error": "Vapi not configured"}
    try:
        response = httpx.post(
            "https://api.vapi.ai/message",
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