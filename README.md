# DebtCall AI — Setup Guide

## Project Structure

```
ai_debt_reminder/
├── backend/
│   ├── main.py              ← FastAPI app entry point
│   ├── database.py          ← DB connection + session
│   ├── models.py            ← SQLAlchemy ORM models
│   ├── schemas.py           ← Pydantic validation schemas
│   ├── auth.py              ← JWT + password hashing
│   ├── routers/
│   │   ├── auth.py          ← POST /auth/login
│   │   ├── admins.py        ← /admins CRUD
│   │   ├── clients.py       ← /clients CRUD + bulk upload
│   │   ├── invoices.py      ← /invoices CRUD + bulk upload + stats
│   │   ├── calls.py         ← /calls read + transcript viewer
│   │   └── settings.py      ← /settings GET + PATCH
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── welcome.html         ← Landing page
│   ├── login.html           ← Admin login
│   └── dashboard.html       ← Full admin dashboard
└── migration.sql            ← Adds scheduler_settings table
```

---

## Step 1 — Database Setup

1. Run your existing schema SQL to create the 4 core tables.
2. Then run `migration.sql` to add the scheduler settings table:

```bash
mysql -u root -p ai_debt_reminder < migration.sql
```

---

## Step 2 — Backend Setup

```bash
cd backend

# Copy and fill in your env file
cp .env.example .env
# Edit .env with your MySQL credentials and a strong SECRET_KEY

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload --port 8000
```

API docs will be available at: **http://localhost:8000/docs**

---

## Step 3 — Frontend Setup

No build step needed. Just open the HTML files directly in a browser,
or serve them with any static file server:

```bash
cd frontend
python -m http.server 3000
```

Then visit: **http://localhost:3000/welcome.html**

---

## API Endpoints Summary

| Method | Endpoint                        | Description                        |
|--------|---------------------------------|------------------------------------|
| POST   | /auth/login                     | Login, returns JWT token           |
| GET    | /auth/me                        | Get current logged-in admin info   |
| GET    | /admins/                        | List all admins                    |
| POST   | /admins/                        | Create admin                       |
| DELETE | /admins/{id}                    | Delete admin                       |
| GET    | /clients/                       | List all clients                   |
| POST   | /clients/                       | Add single client                  |
| PATCH  | /clients/{id}                   | Update client                      |
| DELETE | /clients/{id}                   | Delete client                      |
| POST   | /clients/bulk-upload            | Upload CSV/JSON of clients         |
| GET    | /invoices/                      | List invoices (filterable)         |
| POST   | /invoices/                      | Add single invoice                 |
| PATCH  | /invoices/{id}                  | Update invoice                     |
| DELETE | /invoices/{id}                  | Delete invoice                     |
| POST   | /invoices/bulk-upload           | Upload CSV/JSON of invoices        |
| GET    | /invoices/stats/summary         | Dashboard stat counts              |
| GET    | /calls/                         | List all call logs                 |
| GET    | /calls/{id}/transcript          | View transcript + summary          |
| POST   | /calls/                         | Manual call log (for testing)      |
| DELETE | /calls/{id}                     | Delete call log                    |
| GET    | /settings/                      | Get scheduler config               |
| PATCH  | /settings/                      | Update scheduler config            |
| GET    | /health                         | API + DB health check              |

---

## Bulk Upload Format

### Clients CSV
```
full_name,phone_number,email,timezone
John Smith,+15550001234,john@example.com,America/New_York
Jane Doe,+15550005678,jane@example.com,UTC
```

### Invoices CSV
```
client_id,amount,currency,due_date,status
1,1500.00,USD,2026-03-15,unpaid
2,850.00,GBP,2026-02-28,unpaid
```

---

## When Vapi Credentials are Ready

Add to `.env`:
```
VAPI_API_KEY=your_key_here
VAPI_PHONE_NUMBER_ID=your_phone_id
VAPI_ASSISTANT_ID=your_assistant_id
```

Then add the calling logic in a new file `routers/vapi.py` using the
existing invoice data. The `calls` table is already set up to receive
call results from the Vapi webhook.
