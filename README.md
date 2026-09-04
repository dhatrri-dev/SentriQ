# 🛡️ SentriQ: Real-Time Transaction Risk & Fraud Rule Engine

SentriQ is an enterprise-grade transaction risk assessment and fraud detection backend API built with Python, FastAPI, and SQLAlchemy 2.0. It evaluates incoming payment transactions in real-time, computes dynamic 0–100 risk scores based on behavioral and statistical fraud rules, performs transactional database writes, and assigns automated risk decisions (`ALLOW`, `FLAG_FOR_REVIEW`, `BLOCK`).

---

## 🚀 Key Features

* **⚡ Real-Time Transaction Evaluation (`POST /api/v1/transactions/evaluate`):** Ingests transaction payloads, runs risk rules, and commits transactions, evaluation logs, and investigation cases to the database.
* **🔍 Multi-Factor Fraud Rule Engine:**
  * **Velocity Rule:** Flags cards/users exceeding transaction frequency thresholds in sliding time windows.
  * **Amount Anomaly Rule:** Detects abnormal transaction spikes compared to rolling historical spending averages.
  * **Geo-Velocity (Impossible Travel):** Calculates physical travel distance between consecutive transactions.
  * **Blocklist Matching:** Instantly flags known suspicious IPs, card BINs, or email domains.
* **💾 Transactional Database Write:** Persists evaluation records, audit log items, and investigation cases inside single atomic database transactions.
* **🕵️ Fraud Analyst Case Review Queue (`GET /api/v1/cases/pending` & `POST /api/v1/cases/{id}/resolve`):** Dedicated queue for flagged transactions with manual analyst review and resolution workflows.
* **🗄️ Database & Migrations:** Powered by Supabase (PostgreSQL) / SQLite with SQLAlchemy 2.0 Async ORM and Alembic database schema migrations.

---

## 🛠️ Tech Stack

* **Language:** Python 3.11+
* **Framework:** FastAPI (Async)
* **Server:** Uvicorn
* **Database & ORM:** Supabase (Cloud PostgreSQL) / SQLite + SQLAlchemy 2.0 (Async Session) & Alembic
* **Validation & Settings:** Pydantic v2 & Pydantic-Settings
* **Testing:** Pytest, Pytest-Asyncio, HTTPX

---

## 📁 Project Structure

```text
Backend-Internship/
├── alembic/
│   ├── versions/
│   │   └── 001_initial_schema.py   # Database migration for all 7 core entities
│   └── env.py                      # Async Alembic environment configuration
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── analytics.py    # Analytics overview & fraud metrics
│   │       │   ├── blocklist.py    # Blocklist management API
│   │       │   ├── cases.py        # Investigation case review & resolution
│   │       │   ├── health.py       # Health check API
│   │       │   ├── rules.py        # Fraud risk rule CRUD endpoints
│   │       │   └── transactions.py # Real-time transaction evaluate endpoint
│   │       └── router.py           # v1 API Router aggregation
│   ├── core/
│   │   ├── config.py               # Application settings & environment config
│   │   └── database.py             # SQLAlchemy async engine & session management
│   ├── models/                     # SQLAlchemy ORM Models (7 Entities)
│   │   ├── blocklist.py
│   │   ├── case.py
│   │   ├── evaluation.py
│   │   ├── rule.py
│   │   ├── transaction.py
│   │   └── user.py
│   ├── schemas/                    # Pydantic validation & response schemas
│   │   ├── analytics.py
│   │   ├── blocklist.py
│   │   ├── case.py
│   │   ├── common.py
│   │   ├── evaluation.py
│   │   ├── health.py
│   │   ├── rule.py
│   │   └── transaction.py
│   └── main.py                     # FastAPI application factory, CORS & exception handling
├── tests/
│   ├── conftest.py                 # Async test fixtures & dependency overrides
│   ├── db_fixtures.py              # In-memory SQLite async test database
│   ├── test_api_contracts.py       # Endpoint response contract tests
│   ├── test_create_workflow.py     # Day 4 create workflow & DB persistence tests
│   ├── test_database.py            # Database table & ORM model unit tests
│   └── test_health.py              # Health check endpoint tests
├── .env.example
├── alembic.ini
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## ⚙️ Quickstart & Local Setup

### 1. Clone the Repository & Setup Virtual Environment
```bash
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\activate
# On Linux / macOS:
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Development Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

* **Interactive Swagger UI Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc API Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **Health Check Endpoint:** [http://localhost:8000/health](http://localhost:8000/health)

---

## 🧪 Running Automated Tests

Run the full suite of unit and integration tests (18 tests):

```bash
pytest -v
```
