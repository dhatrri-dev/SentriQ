# 🛡️ SentriQ: Real-Time Transaction Risk & Fraud Rule Engine

SentriQ is an enterprise-grade backend API built with **Python 3.12**, **FastAPI**, and **SQLAlchemy 2.0 Async ORM**. It evaluates payment transactions in real time, calculates dynamic 0–100 risk scores using multi-factor fraud rules and external IP intelligence enrichment, executes atomic transactional writes, and manages analyst investigation queues.

---

## 📋 Table of Contents
- [✨ Key Features](#-key-features)
- [🛠️ Tech Stack](#️-tech-stack)
- [⚙️ Reproducible Setup & Installation](#️-reproducible-setup--installation)
- [🔑 Required Environment Variables](#-required-environment-variables)
- [🗄️ Database Migrations](#️-database-migrations)
- [🚀 Example API Requests](#-example-api-requests)
- [🧪 Running Automated Tests](#-running-automated-tests)
- [🐳 Production Container Deployment](#-production-container-deployment)
- [📚 OpenAPI Documentation](#-openapi-documentation)

---

## ✨ Key Features

* **⚡ Real-Time Risk Engine (`POST /api/v1/transactions/evaluate`):** Evaluates transactions, computes dynamic risk scores, enriches with IP geolocation/proxy risk, and decides automated actions (`ALLOW`, `FLAG_FOR_REVIEW`, `BLOCK`).
* **🔍 Dynamic Risk Rules:**
  * **Velocity Rule:** Flags cards/users exceeding transaction count thresholds in sliding time windows.
  * **Amount Anomaly Rule:** Detects abnormal transaction amounts relative to historical spending averages.
  * **Geo-Velocity (Impossible Travel):** Measures travel distance and speed between consecutive transactions.
  * **Blocklist Rule:** Instantly blocks suspicious IP addresses, email domains, or card BINs.
* **🌐 External Service Integration:** Resilient HTTP client for IP Intelligence lookup with timeouts and fallback circuit-breaker defaults.
* **🕵️ Fraud Case Queue (`GET /api/v1/cases/pending` & `POST /api/v1/cases/{id}/resolve`):** Analyst workflow to review, assign, and resolve flagged fraud cases with audit notes.
* **🔒 Enterprise Security & RBAC:** Role-based access control (`admin`, `analyst`, `client`), password hashing via Passlib/Bcrypt, and OAuth2 JWT authentication.
* **🩺 Dependency-Aware Health Probes:** `/health` endpoint performing live DB `SELECT 1` checks and external dependency status probes.

---

## 🛠️ Tech Stack

* **Language:** Python 3.12+
* **Framework:** FastAPI (Async ASGI)
* **Database & ORM:** PostgreSQL / SQLite with SQLAlchemy 2.0 Async engine & Alembic migrations
* **Security & Auth:** PyJWT, Passlib (Bcrypt), OAuth2 Bearer Tokens
* **Logging & Tracing:** Structured JSON logging (`python-json-logger`) & Request-ID correlation middleware
* **Testing:** Pytest, Pytest-Asyncio, HTTPX

---

## ⚙️ Reproducible Setup & Installation

Follow these step-by-step instructions for a fresh, reproducible local development setup:

### 1. Clone the Repository
```bash
git clone https://github.com/dhatrri-dev/SentriQ.git
cd Backend-Internship
```

### 2. Create and Activate Virtual Environment
- **Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\activate
  ```
- **Linux / macOS:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the sanitized environment template:
```bash
cp .env.example .env
```

---

## 🔑 Required Environment Variables

The application reads configuration from environment variables or a local `.env` file (managed via `pydantic-settings`):

| Variable Name | Required | Default Value | Description |
| :--- | :---: | :--- | :--- |
| `DATABASE_URL` | Yes | `sqlite+aiosqlite:///./sentriq.db` | Async database connection URI (PostgreSQL or SQLite) |
| `SECRET_KEY` | Yes | `[random-256-bit-hex-string]` | Cryptographic secret key for signing JWT tokens |
| `ALGORITHM` | Yes | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `1440` (24h) | JWT access token expiration duration in minutes |
| `ENVIRONMENT` | No | `production` | Runtime environment mode (`development`, `staging`, `production`) |
| `DEBUG` | No | `false` | Enable/disable verbose debug output and SQL query logging |
| `HOST` | No | `0.0.0.0` | Host IP for Uvicorn server binding |
| `PORT` | No | `8000` | Listening port for Uvicorn server |
| `IP_INTEL_SERVICE_URL` | Yes | `https://api.ip-intel.internal` | External IP Intelligence service base URL |
| `IP_INTEL_API_KEY` | Yes | `sentriq_dev_key_sec_123` | API key for IP Intelligence service |
| `IP_INTEL_TIMEOUT_SECONDS` | No | `3.0` | HTTP timeout threshold for IP lookup calls |

---

## 🗄️ Database Migrations

Apply Alembic migrations to set up the database schema:

```bash
# Run all pending migrations
alembic upgrade head
```

To create a new migration after modifying ORM models:
```bash
alembic revision --autogenerate -m "describe_schema_change"
alembic upgrade head
```

---

## 🚀 Example API Requests

Start the development server first:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 1. Register a New User
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "analyst@sentriq.io",
    "password": "SecurePassword123!",
    "full_name": "Jane Doe",
    "role": "analyst"
  }'
```

### 2. Authenticate and Obtain JWT Token
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=analyst@sentriq.io&password=SecurePassword123!"
```
*Response:*
```json
{
  "access_token": "eyJhbGciOiJIUzI1Ni...",
  "token_type": "bearer"
}
```

### 3. Evaluate a Payment Transaction for Risk
```bash
curl -X POST "http://localhost:8000/api/v1/transactions/evaluate" \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "usr_998877",
    "amount": 2500.00,
    "currency": "USD",
    "card_bin": "411111",
    "card_last4": "4242",
    "ip_address": "198.51.100.45",
    "merchant_id": "merch_starbucks",
    "location_lat": 37.7749,
    "location_lon": -122.4194
  }'
```

### 4. Query Health Probe & Active Dependencies
```bash
curl -X GET "http://localhost:8000/health"
```

---

## 🧪 Running Automated Tests

SentriQ includes a 94-test regression and workflow test suite with isolated SQLite database fixtures:

```bash
# Run all tests with detailed verbosity
pytest -v

# Run with coverage report
pytest --cov=app --cov-report=term-missing
```

---

## 🐳 Production Container Deployment

You can build and launch SentriQ using Docker and Docker Compose:

```bash
# Build and start services in background
docker compose up -d --build

# View container status and health probes
docker compose ps

# Check logs
docker compose logs -f app
```

Detailed deployment instructions and operational checklists are available in [`DEPLOYMENT.md`](file:///c:/Users/dhatr/OneDrive/Desktop/Backend-Internship/DEPLOYMENT.md).

---

## 📚 OpenAPI Documentation

Interactive documentation is automatically generated by FastAPI:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema (JSON):** [http://localhost:8000/api/v1/openapi.json](http://localhost:8000/api/v1/openapi.json)
