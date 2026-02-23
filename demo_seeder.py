"""
demo_seeder.py — Populates the database with realistic demo data
for client showcase. Run once before your presentation.

Usage:
    python demo_seeder.py

What it creates:
    - 8 realistic clients (various countries)
    - 10 invoices (mix of overdue, unpaid, paid, processing)
    - 6 call logs with real-looking transcripts and AI summaries
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, date, timedelta
from database import SessionLocal
import models

db = SessionLocal()

print("🌱 Starting demo data seeder...")

# ── STEP 1: Clear old demo data (optional — comment out to keep existing) ──
print("🧹 Clearing existing demo data...")
db.query(models.Call).delete()
db.query(models.Invoice).delete()
db.query(models.Client).delete()
db.commit()
print("✅ Cleared")

# ── STEP 2: Insert Clients ─────────────────────────────────────────────────
print("👥 Inserting clients...")

clients_data = [
    { "full_name": "Jonathan Reed",    "phone_number": "+15550102030", "email": "j.reed@reedlogistics.com",    "timezone": "America/New_York",   "extra_data": {"company": "Reed Logistics",    "segment": "enterprise"} },
    { "full_name": "Elena Rodriguez",  "phone_number": "+15550987654", "email": "elena.r@globaltech.io",       "timezone": "America/Los_Angeles", "extra_data": {"company": "GlobalTech",        "priority": "high"} },
    { "full_name": "Marcus Thorne",    "phone_number": "+442071234567","email": "m.thorne@ukcorp.co.uk",       "timezone": "Europe/London",       "extra_data": {"company": "Thorne Exports",    "segment": "enterprise"} },
    { "full_name": "Priya Sharma",     "phone_number": "+919876543210","email": "priya.s@techind.in",          "timezone": "Asia/Kolkata",        "extra_data": {"company": "TechInd Solutions",  "segment": "mid-market"} },
    { "full_name": "Ahmed Al-Hassan",  "phone_number": "+971501234567","email": "ahmed.h@uaebiz.ae",           "timezone": "Asia/Dubai",          "extra_data": {"company": "UAE Business Corp",  "priority": "high"} },
    { "full_name": "Sofia Mendes",     "phone_number": "+15550333444", "email": "sofia.m@brasilco.com",        "timezone": "America/Sao_Paulo",   "extra_data": {"company": "Brasil Co.",         "segment": "sme"} },
    { "full_name": "Oliver Bennett",   "phone_number": "+442079876543","email": "o.bennett@bennetfirm.co.uk",  "timezone": "Europe/London",       "extra_data": {"company": "Bennett & Associates","segment": "enterprise"} },
    { "full_name": "Fatima Khan",      "phone_number": "+923001234567","email": "fatima.k@pakbusiness.pk",     "timezone": "Asia/Karachi",        "extra_data": {"company": "Pakistan Traders",   "segment": "sme"} },
]

client_objs = []
for c in clients_data:
    obj = models.Client(**c)
    db.add(obj)
    db.flush()
    client_objs.append(obj)

db.commit()
print(f"✅ {len(client_objs)} clients inserted")

# ── STEP 3: Insert Invoices ────────────────────────────────────────────────
print("📄 Inserting invoices...")

today = date.today()

invoices_data = [
    # Overdue — AI should already be calling these
    { "client_id": client_objs[0].client_id, "amount": 12500.00, "currency": "USD", "due_date": today - timedelta(days=18), "status": "overdue" },
    { "client_id": client_objs[1].client_id, "amount": 43000.50, "currency": "USD", "due_date": today - timedelta(days=12), "status": "overdue" },
    { "client_id": client_objs[2].client_id, "amount": 8500.00,  "currency": "GBP", "due_date": today - timedelta(days=7),  "status": "overdue" },
    { "client_id": client_objs[3].client_id, "amount": 95000.00, "currency": "USD", "due_date": today - timedelta(days=5),  "status": "overdue" },

    # Processing — AI called, waiting for payment
    { "client_id": client_objs[4].client_id, "amount": 22000.00, "currency": "USD", "due_date": today - timedelta(days=9),  "status": "processing", "last_reminder_sent": datetime.utcnow() - timedelta(hours=6) },
    { "client_id": client_objs[6].client_id, "amount": 15750.00, "currency": "GBP", "due_date": today - timedelta(days=3),  "status": "processing", "last_reminder_sent": datetime.utcnow() - timedelta(hours=2) },

    # Paid — successfully recovered
    { "client_id": client_objs[5].client_id, "amount": 5800.00,  "currency": "USD", "due_date": today - timedelta(days=20), "status": "paid" },
    { "client_id": client_objs[7].client_id, "amount": 3200.00,  "currency": "USD", "due_date": today - timedelta(days=15), "status": "paid" },

    # Upcoming — not due yet, AI will NOT call
    { "client_id": client_objs[0].client_id, "amount": 8000.00,  "currency": "USD", "due_date": today + timedelta(days=10), "status": "unpaid" },
    { "client_id": client_objs[2].client_id, "amount": 11200.00, "currency": "GBP", "due_date": today + timedelta(days=18), "status": "unpaid" },
]

invoice_objs = []
for inv in invoices_data:
    obj = models.Invoice(**inv)
    db.add(obj)
    db.flush()
    invoice_objs.append(obj)

db.commit()
print(f"✅ {len(invoice_objs)} invoices inserted")

# ── STEP 4: Insert Call Logs with realistic transcripts ────────────────────
print("📞 Inserting call logs...")

calls_data = [
    # Call 1 — Completed, client promised to pay
    {
        "invoice_id":       invoice_objs[0].invoice_id,
        "provider_call_id": "call_vapi_demo_001",
        "call_status":      "completed",
        "duration_seconds": 87,
        "recording_url":    None,
        "transcript": (
            "AI: Hello, may I speak with Jonathan Reed please?\n"
            "Jonathan: Yes, this is Jonathan speaking.\n"
            "AI: Hi Jonathan, I am calling on behalf of our accounts team regarding invoice #"
            + str(invoice_objs[0].invoice_id) +
            " for USD 12,500 which was due 18 days ago. I wanted to check in and see if there is anything we can help with.\n"
            "Jonathan: Oh yes, I completely forgot about that one. Things have been hectic. Can I pay by end of week?\n"
            "AI: Absolutely, we can note that down. So we can expect payment by this Friday?\n"
            "Jonathan: Yes, Friday works. I will process it Thursday actually to be safe.\n"
            "AI: Perfect, thank you Jonathan. I have noted that down. Is there anything else I can help you with?\n"
            "Jonathan: No that is all, thanks for the reminder.\n"
            "AI: Great, have a wonderful day Jonathan. Goodbye."
        ),
        "ai_summary": "Client acknowledged the overdue invoice and committed to payment by Thursday. Positive outcome — follow up if payment not received by Friday.",
    },

    # Call 2 — No answer, SMS sent
    {
        "invoice_id":       invoice_objs[1].invoice_id,
        "provider_call_id": "call_vapi_demo_002",
        "call_status":      "no-answer",
        "duration_seconds": 0,
        "recording_url":    None,
        "transcript":       None,
        "ai_summary":       "Call went unanswered. SMS fallback sent to +15550987654 notifying client of overdue invoice.",
    },

    # Call 3 — Client says already paid
    {
        "invoice_id":       invoice_objs[1].invoice_id,
        "provider_call_id": "call_vapi_demo_003",
        "call_status":      "completed",
        "duration_seconds": 54,
        "recording_url":    None,
        "transcript": (
            "AI: Hello, may I speak with Elena Rodriguez?\n"
            "Elena: Speaking.\n"
            "AI: Hi Elena, I am calling regarding invoice #"
            + str(invoice_objs[1].invoice_id) +
            " for USD 43,000.50 which appears to be outstanding on our records.\n"
            "Elena: I already sent the wire transfer yesterday. Check your accounts department.\n"
            "AI: I completely understand, thank you for letting me know. I will flag this for our accounts team to verify the incoming transfer.\n"
            "Elena: Yes please, I have the transaction reference if you need it.\n"
            "AI: That would be very helpful. Could you share the reference number?\n"
            "Elena: It is TXN-2026-98765.\n"
            "AI: Thank you Elena. I have noted reference TXN-2026-98765. Our team will verify and update the invoice status. Apologies for any inconvenience.\n"
            "Elena: No problem. Goodbye.\n"
            "AI: Thank you Elena, have a great day."
        ),
        "ai_summary": "Client claims payment was already sent via wire transfer. Reference: TXN-2026-98765. Accounts team should verify incoming transfer before closing invoice.",
    },

    # Call 4 — Payment plan requested
    {
        "invoice_id":       invoice_objs[2].invoice_id,
        "provider_call_id": "call_vapi_demo_004",
        "call_status":      "completed",
        "duration_seconds": 132,
        "recording_url":    None,
        "transcript": (
            "AI: Hello, could I speak with Marcus Thorne please?\n"
            "Marcus: Yes, who is calling?\n"
            "AI: Hi Marcus, I am calling from the accounts team regarding invoice #"
            + str(invoice_objs[2].invoice_id) +
            " for GBP 8,500 which was due last week.\n"
            "Marcus: Ah yes. Look, I have been dealing with some cash flow issues this month. Is there any chance we can arrange a payment plan?\n"
            "AI: I appreciate you being upfront about that Marcus. I can certainly note your request for a payment plan and have our accounts manager call you back to arrange the details.\n"
            "Marcus: That would be great. I can do half now and half in 30 days.\n"
            "AI: Understood, I will pass that on. Half now which would be GBP 4,250 and the remainder in 30 days. Is that correct?\n"
            "Marcus: Yes exactly.\n"
            "AI: Perfect, I will make a note of that and someone from our team will contact you within 24 hours to confirm the arrangement.\n"
            "Marcus: Thank you, I appreciate that.\n"
            "AI: Of course Marcus. Have a good day."
        ),
        "ai_summary": "Client requested payment plan: GBP 4,250 now + GBP 4,250 in 30 days. Accounts manager follow-up required within 24 hours to confirm arrangement.",
    },

    # Call 5 — Dispute raised
    {
        "invoice_id":       invoice_objs[3].invoice_id,
        "provider_call_id": "call_vapi_demo_005",
        "call_status":      "completed",
        "duration_seconds": 68,
        "recording_url":    None,
        "transcript": (
            "AI: Hello, is this Priya Sharma?\n"
            "Priya: Yes, speaking.\n"
            "AI: Hi Priya, I am calling regarding invoice #"
            + str(invoice_objs[3].invoice_id) +
            " for USD 95,000 which is currently overdue.\n"
            "Priya: I think there is a mistake on that invoice. The amount should be USD 75,000, not 95,000. We discussed a 20% discount at the last meeting.\n"
            "AI: I understand and I apologise for any confusion. I have noted the dispute regarding the invoice amount and the mentioned discount agreement. I will escalate this to our accounts team immediately.\n"
            "Priya: Yes please. I have the email from your sales team confirming the discount.\n"
            "AI: That is very helpful. Our team will review the correspondence and get back to you within 2 business days.\n"
            "Priya: Thank you.\n"
            "AI: Thank you Priya. Have a good day."
        ),
        "ai_summary": "Client disputes invoice amount. Claims agreed price is USD 75,000 not USD 95,000 due to 20% discount agreed with sales team. Client has supporting email. URGENT: Accounts team must review before pursuing payment.",
    },

    # Call 6 — Busy, rescheduled
    {
        "invoice_id":       invoice_objs[4].invoice_id,
        "provider_call_id": "call_vapi_demo_006",
        "call_status":      "completed",
        "duration_seconds": 22,
        "recording_url":    None,
        "transcript": (
            "AI: Hello, may I speak with Ahmed Al-Hassan?\n"
            "Ahmed: Yes, I am in a meeting right now. Can you call back in 2 hours?\n"
            "AI: Of course Ahmed, I apologise for the interruption. I will have someone call you back in approximately 2 hours regarding an important invoice matter.\n"
            "Ahmed: Thank you, goodbye.\n"
            "AI: Thank you, goodbye."
        ),
        "ai_summary": "Client was in a meeting. Requested callback in 2 hours. Schedule follow-up call.",
    },
]

for call in calls_data:
    obj = models.Call(**call)
    db.add(obj)

db.commit()
print(f"✅ {len(calls_data)} call logs inserted")

# ── SUMMARY ────────────────────────────────────────────────────────────────
print("\n" + "="*55)
print("✅ DEMO DATA SEEDING COMPLETE!")
print("="*55)
print(f"  👥 Clients inserted:   {len(client_objs)}")
print(f"  📄 Invoices inserted:  {len(invoice_objs)}")
print(f"  📞 Call logs inserted: {len(calls_data)}")
print("\n  Invoice breakdown:")
print("    Overdue:     4  ← AI would be calling these")
print("    Processing:  2  ← AI called, awaiting payment")
print("    Paid:        2  ← Successfully recovered")
print("    Upcoming:    2  ← Not due yet")
print("\n  Call log breakdown:")
print("    Completed:   4  (promise to pay, dispute, plan, busy)")
print("    No Answer:   1  (SMS fallback triggered)")
print("    Total:       6  realistic conversations")
print("\n🚀 Open your dashboard to see the data!")
print("   http://localhost:3000/frontend/dashboard.html")
print("="*55)

db.close()
