"""
main.py — FastAPI application entry point.
Run with:  uvicorn main:app --reload --port 8000
Docs at:   http://localhost:8000/docs
"""

import os
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import Base, check_connection, engine
from routers  import auth, admins, clients, invoices, calls, settings
from routers  import webhook
from scheduler import start_scheduler, stop_scheduler
from vapi_service import is_vapi_configured

load_dotenv()

logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    if check_connection():
        logger.info("✅ Database connected successfully")
    else:
        logger.error("❌ Database connection FAILED — check your .env settings")

    start_scheduler()

    if is_vapi_configured():
        logger.info("✅ Vapi credentials found — AI calling is ACTIVE")
    else:
        logger.warning("⚠️  Vapi credentials NOT configured — AI calling is DISABLED")
        logger.warning("⚠️  Add VAPI_API_KEY, VAPI_PHONE_NUMBER_ID, VAPI_ASSISTANT_ID to .env to enable")

    yield

    stop_scheduler()
    logger.info("👋 Server shutting down")


app = FastAPI(
    title       = "AI Debt Reminder — Admin API",
    description = "Backend API for managing clients, invoices, AI call logs, and scheduler settings.",
    version     = "1.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,

    allow_origin_regex = r"https://.*\.vercel\.app",
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

app.include_router(auth.router)
app.include_router(admins.router)
app.include_router(clients.router)
app.include_router(invoices.router)
app.include_router(calls.router)
app.include_router(settings.router)
app.include_router(webhook.router)

# ── Serve frontend HTML files ──────────────────────────────────────────────
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "AI Debt Reminder API is running"}


@app.get("/health", tags=["Health"])
def health():
    return {
        "api":       "ok",
        "database":  "ok" if check_connection() else "error",
        "vapi":      "configured" if is_vapi_configured() else "not_configured",
        "scheduler": "running",
    }