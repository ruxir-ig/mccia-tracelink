# 🔗 TraceLink — Manufacturing Traceability Control System

> **Track any dispatch order from factory floor to customer in 30 seconds.**  
> End-to-end traceability for raw materials → production → QC → dispatch with full audit trails.

---

## 📋 Table of Contents

- [What is TraceLink?](#what-is-tracelink)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Authentication](#authentication)
- [User Roles](#user-roles)
- [API Reference](#api-reference)
- [Data Pipeline](#data-pipeline)
- [Multilingual Support](#multilingual-support)
- [Deployment](#deployment)
- [Environment Variables](#environment-variables)

---

## What is TraceLink?

TraceLink is a **production-grade manufacturing traceability system** built for quality control teams, plant managers, and compliance officers. It connects every step of the manufacturing chain:

```
Raw Material Receipt → Production Batches → QC Inspection → Dispatch → Customer
        ↓                    ↓                  ↓              ↓
   Supplier Data        Machine/Operator     Pass/Fail      Order Tracking
   Lot Numbers          Shift Records        Defect Rates   Batch References
```

### The Problem It Solves

When a customer reports a defect, manufacturers need to answer:
- *"Which raw material lot was used in this batch?"*
- *"What other dispatch orders used the same lot?"*
- *"Which machine/operator produced this batch?"*
- *"Did QC flag anything?"*

TraceLink answers all of these **in under 30 seconds** with full audit trails. It now features an **AI Assistant**, **Dynamic Data Imputation**, and a **Contamination Blast Radius** module for advanced predictive impact tracking.

---

## Key Features

| Feature | Description | Who Uses It |
|---------|-------------|-------------|
| 🔍 **Trace Engine** | Forward/backward trace from any dispatch order | Quality, Managers |
| 🚨 **Contamination Blast Radius** | Deep analytical impact simulation when a raw lot is flagged (Financial Exposure, Escaped Shipments) | Quality, Compliance |
| 🤖 **Conversational AI** | Natural language logistics query assistant | Everyone |
| 📊 **Shift Intelligence** | Dynamic dashboard highlighting the worst-performing shift in real-time | Managers, Leadership |
| 🧠 **Dynamic Imputation** | 3-tier probabilistic rule engine for auto-resolving missing batch IDs during CSV ingestion | Data Team |
| 📝 **Shop-Floor Logger** | Offline-first batch entry with auto-shift detection | Operators |
| 📁 **Import** | Bulk CSV upload with real-time validation and imputation | Quality, Data Team |
| 🔗 **Review Queue** | Approve/reject inferred trace links | Supervisors |
| 📋 **Compliance** | Corrective actions (8D/CAPA) tracking | Quality, Compliance |
| 📋 **Data Audit** | Complete transparency into pipeline imputation logic and temporal integrity | Admins |
| 🔒 **Audit Log** | Every action logged with user, timestamp, request ID | Admins |
| 🌐 **Bilingual Interface** | English + Marathi UI with one-click toggle | Everyone |
| 📖 **Guided Tour** | Interactive onboarding for new users | Everyone |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │ Firebase │ │   i18n   │ │ Offline  │             │
│  │   Auth   │ │ EN / HI  │ │  Queue   │             │
│  └────┬─────┘ └──────────┘ └────┬─────┘             │
│       │                          │                  │
│       ▼                          ▼                  │
│  ┌─────────────────────────────────────┐            │
│  │         api.ts (Firebase ID Token)  │            │
│  └──────────────────┬──────────────────┘            │
└─────────────────────┼───────────────────────────────┘
                      │ HTTPS + Bearer Token
┌─────────────────────┼───────────────────────────────┐
│                     ▼                               │
│            FastAPI Backend (Python)                 │
│  ┌──────────────────────────────────────┐           │
│  │  firebase-admin (Token Verification) │           │
│  └──────────────────────────────────────┘           │
│  ┌──────┐ ┌───────┐ ┌────────┐ ┌───────┐            │
│  │ RBAC │ │ Audit │ │ Import │ │ CAPA  │            │
│  └──────┘ └───────┘ └────────┘ └───────┘            │
│                     │                               │
│            SQLite (WAL mode)                        │
│  ┌──────────────────────────────────────┐           │
│  │ 12 tables: users, production_batches,│           │
│  │ qc_inspections, dispatch_orders, ... │           │
│  └──────────────────────────────────────┘           │
└─────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **Firebase project** with Email/Password auth enabled

### 1. Clone & Setup Backend

```bash
cd mccia-tracelink/backend
pip install -r requirements.txt
```

### 2. Firebase Setup

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Create a project (or use existing: `tracelink-793ba`)
3. Enable **Authentication → Sign-in method → Email/Password**
4. (Optional) Enable **Google** sign-in
5. Go to **Project Settings → Service accounts → Generate new private key**
6. Save as `backend/serviceAccountKey.json`

> ⚠️ **Never commit `serviceAccountKey.json` to git!** It's in `.gitignore`.

### 3. Initialize Database

```bash
cd backend
python -c "from app.pipeline import rebuild_database; print(rebuild_database())"
```

### 4. Start Backend

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 5. Setup & Start Frontend

```bash
cd frontend
npm install
npm run dev
```

### 6. Open & Login

- Frontend: **http://localhost:5173**
- API Docs: **http://localhost:8000/api/docs**
- Register with email/password or sign in with Google

### 7. Promote Yourself to Admin

```bash
cd backend
python -c "
from app.db import connect
conn = connect()
conn.execute('UPDATE users SET role=? WHERE email=?', ('admin', 'YOUR_EMAIL'))
conn.commit()
print('Done')
conn.close()
"
```

---

## Project Structure

```
mccia-tracelink/
├── backend/
│   ├── app/
│   │   ├── api/                    # Versioned route modules
│   │   │   ├── admin_routes.py     # Audit logs, users, health
│   │   │   ├── alert_routes.py     # Lot contamination alerts
│   │   │   ├── auth_routes.py      # Firebase sync, /me, roles
│   │   │   ├── compliance_routes.py # CAPA/8D actions
│   │   │   ├── dashboard_routes.py # KPI metrics
│   │   │   ├── import_routes.py    # CSV upload + validation
│   │   │   ├── operator_routes.py  # Batch entry + approval
│   │   │   ├── review_routes.py    # Unresolved link queue
│   │   │   └── trace_routes.py     # Dispatch trace + export
│   │   ├── auth.py                 # Firebase token verification + RBAC
│   │   ├── config.py               # Pydantic settings
│   │   ├── db.py                   # SQLite connection (WAL mode)
│   │   ├── linking.py              # Trace link scoring engine
│   │   ├── main.py                 # FastAPI app + lifespan
│   │   ├── middleware.py           # Audit logging middleware
│   │   ├── pipeline.py             # Schema + CSV data loader
│   │   └── schemas.py              # Pydantic models
│   ├── requirements.txt
│   └── serviceAccountKey.json      # 🔒 (gitignored)
├── frontend/
│   ├── src/
│   │   ├── auth/
│   │   │   ├── AuthContext.tsx      # Firebase auth state
│   │   │   └── LoginPage.tsx        # Login + Register + Google
│   │   ├── terminal/
│   │   │   ├── App.tsx              # All pages + routing
│   │   │   └── styles.css           # Terminal HUD theme
│   │   ├── api.ts                   # API layer with Firebase tokens
│   │   ├── firebase.ts              # Firebase SDK config
│   │   ├── i18n.ts                  # Multilingual translations
│   │   ├── offlineQueue.ts          # IndexedDB offline sync
│   │   └── main.tsx                 # React entry point
│   └── package.json
├── raw_materials_log.csv            # Sample data
├── production_log.csv
├── qc_inspection.csv
├── dispatch_log.csv
├── supplier_master.csv
├── defect_complaints.csv
└── README.md
```

---

## Authentication

TraceLink uses **Firebase Authentication** for secure, production-grade auth:

- **Email/Password** — Standard registration and login
- **Google Sign-In** — One-click OAuth via Google
- **Token Refresh** — Automatic every 50 minutes
- **Session Persistence** — Survives browser refresh

The backend verifies Firebase ID tokens using `firebase-admin` SDK and maps each user to a local role in the `users` table.

---

## User Roles

| Role | Trace | Alert | Operator | Dashboard | Import | Review | Compliance | Admin |
|------|-------|-------|----------|-----------|--------|--------|------------|-------|
| `operator` | ✅ | ✅ | ✅ | ✅ | ❌ | 👀 View | ❌ | ❌ |
| `supervisor` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ Approve | ❌ | ❌ |
| `quality` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `manager` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `admin` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

New users default to `operator`. Admins can promote via API:

```bash
# PATCH /api/v1/auth/users/{user_id}/role?role=admin
```

---

## API Reference

All endpoints require a Firebase ID token in the `Authorization: Bearer <token>` header.

| Method | Endpoint | Role Required | Description |
|--------|----------|---------------|-------------|
| POST | `/api/v1/auth/firebase-sync` | any | Sync Firebase user → local DB |
| GET | `/api/v1/auth/me` | any | Current user info |
| GET | `/api/v1/trace/dispatch/{id}` | any | Full trace for dispatch order |
| GET | `/api/v1/trace/dispatch/{id}/export` | any | CSV export of trace |
| GET | `/api/v1/alerts/lots/{lot}` | any | Lot contamination alert with Blast Radius |
| GET | `/api/v1/alerts/lots/{lot}/export` | any | CSV export of alert |
| POST | `/api/v1/operator/batches` | operator+ | Create batch entry |
| GET | `/api/v1/operator/batches/recent` | operator+ | Recent entries |
| GET | `/api/v1/dashboard/metrics` | any | Dashboard KPIs including Shift Intelligence |
| POST | `/api/v1/imports` | quality+ | Upload CSV file (triggers dynamic imputation) |
| GET | `/api/v1/review/unresolved-links` | any | List unresolved links |
| POST | `/api/v1/review/.../approve` | supervisor+ | Approve link |
| POST | `/api/v1/compliance/corrective-actions` | quality+ | Create CAPA |
| GET | `/api/v1/ai/query` | any | Conversational AI logistics queries |
| GET | `/api/v1/admin/audit-events` | admin | View user audit log |
| GET | `/api/v1/admin/pipeline-audit` | admin | View data pipeline imputation stats & anomalies |
| GET | `/api/v1/admin/health` | any | System health |

---

## Data Pipeline

TraceLink processes 6 CSV files to build its traceability database:

| File | Records | Key Fields |
|------|---------|------------|
| `raw_materials_log.csv` | ~2,400 | lot_number, supplier_id, material_type |
| `production_log.csv` | ~5,400 | batch_id, input_lot_ref, machine_id |
| `qc_inspection.csv` | ~5,400 | batch_id, pass_fail, defect_rate_pct |
| `dispatch_log.csv` | ~1,800 | order_id, batch_ref, customer_id |
| `supplier_master.csv` | 6 | supplier_id, supplier_name, approved_status |
| `defect_complaints.csv` | 3 | complaint_id, root_cause, financial_impact |

### Trace Link Scoring

When production records reference a raw material lot, TraceLink scores the confidence of the link:

- **Deterministic** (≥80%) — Direct lot match with strong evidence
- **Inferred** (<80%) — Ambiguous match needing human review
- **Reviewed** — Supervisor-approved inferred link

Scoring factors (all data-driven, no hardcoding):
- Defect-material correlation
- Supplier mention in complaints
- Quality grade risk
- Supplier approval status

### Dynamic Imputation Engine

When raw production records are uploaded with missing or null batch IDs, TraceLink's Dynamic Imputation Engine uses a 3-tier probabilistic rule system:

- **Rule 1 (75% Confidence)**: Interpolates based on identical timestamps for the same machine ID and operator.
- **Rule 2 (45% Confidence)**: Interpolates based on preceding timestamps on the same machine ID.
- **Rule 3 (0% Confidence Fallback)**: Assigns a synthetic unique batch ID to prevent data loss.

This ensures zero data drop during ingestion while preserving pipeline transparency. You can monitor imputation breakdown directly in the **Data Audit Dashboard**.

---

## Multilingual Support

TraceLink supports **English** and **Marathi** with one-click toggle on the Shop-Floor Logger page to seamlessly support localized factory operations. The i18n system covers:
- Navigation labels
- Page titles and descriptions
- Form labels and placeholders
- Error messages
- Onboarding guide text

---

## Deployment

### Production Build

```bash
# Frontend
cd frontend && npm run build

# Backend serves the built frontend automatically
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `dev` | `dev`, `staging`, or `production` |
| `GOOGLE_APPLICATION_CREDENTIALS` | `backend/serviceAccountKey.json` | Firebase service account key path |
| `CORS_ORIGINS` | `*` | Allowed origins (restrict in production) |
| `FIREBASE_PROJECT_ID` | `tracelink-793ba` | Firebase project ID |

### Production Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Restrict `CORS_ORIGINS` to your domain
- [ ] Ensure `serviceAccountKey.json` is secure
- [ ] Set up HTTPS (nginx/caddy reverse proxy)
- [ ] Configure database backups
- [ ] Set up monitoring/alerting

---

## License

MIT — Built for MMCIA Manufacturing Traceability.