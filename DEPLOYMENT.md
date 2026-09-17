# 🚀 SentriQ Production Deployment Guide & Readiness Checklist

This document outlines the step-by-step procedures, environment configurations, security checklists, and startup commands required to deploy **SentriQ** to production.

---

## 📋 Deployment Readiness Checklist

### 1. Security & Environment Controls
- [x] **Debug Mode Disabled**: Ensure `DEBUG=false` in production environment settings.
- [x] **Secrets Excluded from Git**: Confirm `.env` and sensitive DB credentials are ignored in `.gitignore`.
- [x] **Environment Template Provided**: Verified sanitized `.env.example` file is included in repository root.
- [x] **Strong Secret Keys**: Generate a 64-character random hex string for `SECRET_KEY` (`openssl rand -hex 32`).
- [x] **Non-Root Container Security**: Docker container executes under restricted system user (`appuser`).

### 2. Operational Health & Probes
- [x] **Active Health Probe**: `/api/v1/health` actively probes database connectivity (`SELECT 1`) and external IP intelligence service reachability.
- [x] **HTTP Status Code Mapping**: Returns `200 OK` when all dependencies are healthy, or `503 Service Unavailable` if core database connectivity fails.
- [x] **Request Tracing**: `RequestTracingMiddleware` propagates unique `x-request-id` header for log aggregation and distributed tracing.

---

## 🛠️ Production Startup Commands

### Option A: Local / Native Uvicorn Execution
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Apply database migrations:
   ```bash
   alembic upgrade head
   ```
3. Launch production Uvicorn server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

### Option B: Docker Compose Deployment (Recommended)
1. Build and launch application and PostgreSQL database containers:
   ```bash
   docker-compose up -d --build
   ```
2. Verify container operational status and health checks:
   ```bash
   docker-compose ps
   ```
3. View real-time application logs:
   ```bash
   docker-compose logs -f api
   ```

---

## 🔍 Post-Deployment Verification Commands

1. **Verify Health & Dependencies**:
   ```bash
   curl -i http://localhost:8000/api/v1/health
   ```
2. **Verify OpenAPI Swagger UI**:
   Navigate to `http://localhost:8000/docs` in your web browser.
3. **Execute Automated Test Suite**:
   ```bash
   pytest tests/ -v
   ```
