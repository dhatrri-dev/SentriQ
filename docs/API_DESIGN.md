# 🛡️ SentriQ — API Design & Entity Relationship Specification

## 1. Domain Entities & Relationships

```mermaid
erDiagram
    USERS ||--o{ TRANSACTIONS : "initiates"
    USERS ||--o{ INVESTIGATION_CASES : "subject of"
    TRANSACTIONS ||--|| EVALUATION_LOGS : "evaluated as"
    TRANSACTIONS ||--o| INVESTIGATION_CASES : "triggers review in"
    RISK_RULES ||--o{ EVALUATION_LOG_ITEMS : "configured in"
    EVALUATION_LOGS ||--o{ EVALUATION_LOG_ITEMS : "contains"
    BLOCKLIST_ENTITIES }o--|| USERS : "added by admin"

    USERS {
        uuid id PK
        string email UK
        string full_name
        string role "ADMIN | ANALYST | CLIENT"
        decimal avg_monthly_spend
        int total_transaction_count
        datetime created_at
        datetime updated_at
    }

    TRANSACTIONS {
        uuid id PK
        uuid user_id FK
        string card_hash
        string card_bin
        decimal amount
        string currency "USD | EUR | INR | GBP"
        string ip_address
        decimal latitude
        decimal longitude
        string country
        string city
        string device_id
        string status "PENDING | APPROVED | FLAGGED | BLOCKED"
        int risk_score "0 to 100"
        datetime timestamp
        datetime created_at
    }

    RISK_RULES {
        uuid id PK
        string rule_code UK "VELOCITY_60S | AMOUNT_SPIKE_5X | IMPOSSIBLE_TRAVEL | BLOCKLIST_HIT"
        string name
        string rule_type "VELOCITY | AMOUNT_ANOMALY | GEO_DISTANCE | BLOCKLIST"
        decimal threshold_value
        int weight_points "1 to 100"
        boolean is_active
        string description
        datetime created_at
    }

    EVALUATION_LOGS {
        uuid id PK
        uuid transaction_id FK, UK
        int final_score "0 to 100"
        string decision "ALLOW | FLAG_FOR_REVIEW | BLOCK"
        int rules_triggered_count
        decimal execution_time_ms
        datetime evaluated_at
    }

    EVALUATION_LOG_ITEMS {
        uuid id PK
        uuid evaluation_log_id FK
        uuid rule_id FK
        string rule_code
        int points_assigned
        string reason
        json details
    }

    INVESTIGATION_CASES {
        uuid id PK
        uuid transaction_id FK, UK
        uuid user_id FK
        uuid assigned_analyst_id FK
        string status "PENDING | IN_REVIEW | RESOLVED_APPROVED | RESOLVED_BLOCKED"
        string priority "LOW | MEDIUM | HIGH | CRITICAL"
        string resolution_notes
        datetime resolved_at
        datetime created_at
    }

    BLOCKLIST_ENTITIES {
        uuid id PK
        string entity_type "IP | CARD_BIN | CARD_HASH | EMAIL_DOMAIN | COUNTRY"
        string entity_value
        string reason
        boolean is_active
        datetime expires_at
        datetime created_at
    }
```

---

## 2. API Contract Specification

### Base URL: `/api/v1`

---

### Endpoint 1: Real-Time Transaction Ingestion & Evaluation
* **Path:** `POST /api/v1/transactions/evaluate`
* **Description:** Evaluates an incoming transaction against active fraud rules and returns an immediate decision (`ALLOW`, `FLAG_FOR_REVIEW`, `BLOCK`).

#### Request Contract:
```json
{
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "card_hash": "a1b2c3d4e5f67890abcdef1234567890abcdef12",
  "card_bin": "411111",
  "amount": 2500.00,
  "currency": "USD",
  "ip_address": "198.51.100.42",
  "location": {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "country": "US",
    "city": "New York"
  },
  "device_id": "dev_xyz_98765",
  "timestamp": "2026-09-02T10:00:00Z"
}
```

#### Success Response (`200 OK`):
```json
{
  "transaction_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "risk_score": 85,
  "decision": "BLOCK",
  "rules_triggered": [
    {
      "rule_code": "AMOUNT_SPIKE_5X",
      "rule_name": "Amount Spike Anomaly",
      "points": 50,
      "reason": "Transaction amount $2500.00 exceeds 5x user average ($350.00)"
    },
    {
      "rule_code": "IMPOSSIBLE_TRAVEL",
      "rule_name": "Impossible Geo-Velocity",
      "points": 35,
      "reason": "Distance from previous transaction is 5,585 km within 12 minutes (Speed: 27,925 km/h)"
    }
  ],
  "execution_time_ms": 8.45,
  "evaluated_at": "2026-09-02T10:00:00.125Z"
}
```

#### Error Responses:
* `422 Unprocessable Entity` — Invalid schema payload (e.g., negative amount, invalid IP format, unsupported currency).
* `400 Bad Request` — Missing required transaction fields.
* `500 Internal Server Error` — Engine processing error.

---

### Endpoint 2: List Pending Fraud Investigation Cases
* **Path:** `GET /api/v1/cases/pending`
* **Query Parameters:** `page` (default 1), `size` (default 20), `priority` (optional filter)
* **Success Response (`200 OK`):**
```json
{
  "total": 1,
  "page": 1,
  "size": 20,
  "items": [
    {
      "case_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
      "transaction_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "amount": 1200.00,
      "currency": "USD",
      "risk_score": 55,
      "priority": "HIGH",
      "status": "PENDING",
      "created_at": "2026-09-02T09:45:00Z"
    }
  ]
}
```

---

### Endpoint 3: Resolve Fraud Investigation Case
* **Path:** `POST /api/v1/cases/{case_id}/resolve`
* **Request Contract:**
```json
{
  "action": "APPROVE",
  "resolution_notes": "Customer confirmed legitimate transaction via phone verification."
}
```
* **Success Response (`200 OK`):**
```json
{
  "case_id": "c1a2b3c4-d5e6-7f8a-9b0c-1d2e3f4a5b6c",
  "status": "RESOLVED_APPROVED",
  "analyst_id": "e8f7a6b5-c4d3-2e1f-0a9b-8c7d6e5f4a3b",
  "resolution_notes": "Customer confirmed legitimate transaction via phone verification.",
  "resolved_at": "2026-09-02T10:15:30Z"
}
```
* **Error Response (`404 Not Found`):** Case ID does not exist.

---

### Endpoint 4: Manage Risk Rules (Admin)
* **Path:** `GET /api/v1/rules` — List all rules.
* **Path:** `POST /api/v1/rules` — Create a new rule.
* **Path:** `PATCH /api/v1/rules/{rule_id}` — Update threshold or point weights.

---

### Endpoint 5: Manage Blocklist & Allowlist
* **Path:** `GET /api/v1/blocklist` — List blocked entities.
* **Path:** `POST /api/v1/blocklist` — Add an entity (IP, BIN, Email domain).
* **Path:** `DELETE /api/v1/blocklist/{id}` — Unblock entity.

---

### Endpoint 6: Fraud Analytics & Metrics
* **Path:** `GET /api/v1/analytics/overview`
* **Success Response (`200 OK`):**
```json
{
  "total_transactions_evaluated": 12450,
  "total_amount_evaluated": 3450000.00,
  "total_fraud_blocked_amount": 182500.00,
  "decisions_breakdown": {
    "ALLOW": 11800,
    "FLAG_FOR_REVIEW": 450,
    "BLOCK": 200
  },
  "top_triggered_rules": [
    { "rule_code": "VELOCITY_60S", "count": 185 },
    { "rule_code": "AMOUNT_SPIKE_5X", "count": 142 },
    { "rule_code": "IMPOSSIBLE_TRAVEL", "count": 93 }
  ]
}
```
