# 🛡️ SentriQ: Real-Time Transaction Risk & Fraud Rule Engine

SentriQ is an enterprise-grade transaction risk assessment and fraud detection backend API built with Python and FastAPI. It evaluates incoming payment transactions in real-time ($<15\text{ms}$), computes dynamic 0–100 risk scores based on behavioral and statistical fraud rules, and assigns automated risk decisions (`ALLOW`, `FLAG_FOR_REVIEW`, `BLOCK`).

---

## 🚀 Key Features

* **⚡ Real-Time Transaction Ingestion & Evaluation:** Ingests transaction payloads and returns immediate risk decisions with granular rule breakdown.
* **🔍 Multi-Factor Rule Engine:**
  * **Velocity Rule:** Flags cards/users exceeding transaction thresholds in sliding time windows.
  * **Amount Anomaly Rule:** Detects abnormal transaction spikes compared to rolling 30-day user spending averages.
  * **Geo-Velocity (Impossible Travel):** Calculates distance (Haversine formula) to flag physically impossible travel between transactions.
* **⚖️ Dynamic 0–100 Risk Scoring:** Weighted rule scoring model with full audit logging.
* **🕵️ Fraud Analyst Case Review Queue:** Dedicated investigation queue for flagged transactions with manual approval/rejection workflows.
* **🗄️ Cloud Database:** Powered by Supabase (PostgreSQL) with SQLAlchemy 2.0 ORM.

---

## 🛠️ Tech Stack

* **Language:** Python 3.11+
* **Framework:** FastAPI (Async)
* **Server:** Uvicorn
* **Database:** Supabase (Cloud PostgreSQL) / SQLite with SQLAlchemy 2.0
* **Validation & Settings:** Pydantic v2 & Pydantic-Settings
* **Testing:** Pytest, Pytest-Asyncio, HTTPX

---

## 📁 Project Structure

```text
Backend-Internship/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   └── health.py       # Health check API endpoint
│   │       └── router.py           # v1 API Router
│   ├── core/
│   │   └── config.py               # Application settings & environment config
│   ├── schemas/
│   │   └── health.py               # Pydantic schemas for health responses
│   └── main.py                     # FastAPI application factory & root routing
├── tests/
│   ├── conftest.py                 # Async test fixtures
│   └── test_health.py              # Health endpoint unit tests
├── .env.example
├── .gitignore
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

```bash
pytest
```
