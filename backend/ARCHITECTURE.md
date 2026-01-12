# HealthOps Backend Architecture

## Overview

HealthOps is a healthcare operations management system with AI-powered referral processing, caregiver matching, and scheduling.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React - Port 3000)                           │
│   Dashboard │ Journey Board │ Schedule Client │ Referral Table │ Caregiver Table   │
└───────────────────────────────────────┬─────────────────────────────────────────────┘
                                        │ HTTP REST API
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           FASTAPI BACKEND (Port 8000)                               │
│                                   app.py                                            │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                          API ENDPOINTS                                       │   │
│  ├─────────────────────────────────────────────────────────────────────────────┤   │
│  │                                                                             │   │
│  │  📋 REFERRALS                    🗓️ SCHEDULING                              │   │
│  │  GET  /api/v1/referrals          POST /api/v1/scheduling/apply              │   │
│  │  POST /api/v1/intake/simulate    POST /api/v1/schedule/confirm              │   │
│  │  POST /api/v1/intake/from-pdf    GET  /api/v1/agent/pending-referrals       │   │
│  │                                                                             │   │
│  │  🚀 JOURNEY                      🤖 AI AGENTS                               │   │
│  │  GET  /api/v1/journey/board      POST /api/v1/agent/process-referral        │   │
│  │  GET  /api/v1/referrals/{id}/    POST /api/v1/crew/process-referral         │   │
│  │       journey                    POST /api/v1/crew/process-batch            │   │
│  │  POST /api/v1/referrals/{id}/                                               │   │
│  │       journey/advance            📊 DASHBOARD                               │   │
│  │                                  GET  /api/v1/dashboard-metrics             │   │
│  │  👥 CAREGIVERS                   GET  /api/v1/ops/summary                   │   │
│  │  GET  /api/v1/caregivers         GET  /api/v1/stats                         │   │
│  │                                                                             │   │
│  │  📧 NOTIFICATIONS                🖼️ DOCUMENT PROCESSING                     │   │
│  │  POST /api/v1/email/             POST /api/v1/process-image                 │   │
│  │       send-notification          POST /api/v1/upload-image                  │   │
│  │                                                                             │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                        │                                            │
└────────────────────────────────────────┼────────────────────────────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
┌──────────────────────────┐ ┌──────────────────────┐ ┌──────────────────────────┐
│     🤖 AI SERVICES       │ │   💾 DATA LAYER      │ │   📨 EXTERNAL SERVICES   │
├──────────────────────────┤ ├──────────────────────┤ ├──────────────────────────┤
│                          │ │                      │ │                          │
│  agent_workflow.py       │ │  db_service.py       │ │  email_service.py        │
│  ┌────────────────────┐  │ │  (PostgreSQL)        │ │  (Gmail SMTP)            │
│  │ Agent 1: Validation│  │ │                      │ │                          │
│  │ (Gemini AI)        │  │ │  Tables:             │ │  landingai_service.py    │
│  └─────────┬──────────┘  │ │  - referrals         │ │  (Document OCR)          │
│            ▼             │ │  - caregivers        │ │                          │
│  ┌────────────────────┐  │ │  - journey_overrides │ │  Google Gemini API       │
│  │ Agent 2: Matching  │  │ │                      │ │  (AI Recommendations)    │
│  │ (Gemini AI)        │  │ │  CSV Files:          │ │                          │
│  └─────────┬──────────┘  │ │  - referrals.csv     │ │                          │
│            ▼             │ │  - caregivers.csv    │ │                          │
│  ┌────────────────────┐  │ │                      │ │                          │
│  │ Agent 3: Scheduling│  │ │                      │ │                          │
│  │ (Gemini AI)        │  │ │                      │ │                          │
│  └────────────────────┘  │ │                      │ │                          │
│                          │ │                      │ │                          │
│  crew_workflow.py        │ │  faiss_service.py    │ │                          │
│  (CrewAI Multi-Agent)    │ │  (Vector Search)     │ │                          │
│                          │ │                      │ │                          │
│  rules_engine.py         │ │                      │ │                          │
│  (Business Rules)        │ │                      │ │                          │
│                          │ │                      │ │                          │
│  sorting_agent.py        │ │                      │ │                          │
│  (Priority Sorting)      │ │                      │ │                          │
│                          │ │                      │ │                          │
└──────────────────────────┘ └──────────────────────┘ └──────────────────────────┘
```

---

## Key Workflows

### 1. 3-Agent Scheduling Workflow

**Endpoint:** `POST /api/v1/agent/process-referral`

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌──────────────┐
│   Referral  │────▶│ Agent 1:         │────▶│ Agent 2:        │────▶│ Agent 3:     │
│   Input     │     │ VALIDATION       │     │ CAREGIVER MATCH │     │ SCHEDULING   │
│             │     │ (Gemini AI)      │     │ (Gemini AI)     │     │ (Gemini AI)  │
└─────────────┘     └──────────────────┘     └─────────────────┘     └──────────────┘
                           │                        │                       │
                           ▼                        ▼                       ▼
                    ┌──────────────┐         ┌─────────────┐         ┌─────────────┐
                    │ Check:       │         │ SKIPPED if: │         │ Result:     │
                    │ - Auth valid │         │ - Docs ❌    │         │ - CAN/HOLD  │
                    │ - Dates OK   │         │ - Home ❌    │         │ - Priority  │
                    │ - Complete   │         │              │         │ - Next Steps│
                    └──────────────┘         │ RUNS if:     │         └─────────────┘
                                             │ - Docs ✅    │
                                             │ - Home ✅    │
                                             └─────────────┘
```

#### Agent Details:

| Agent | Purpose | AI Model | Conditions |
|-------|---------|----------|------------|
| **Agent 1: Validation** | Validates referral completeness | Google Gemini | Always runs |
| **Agent 2: Matching** | Finds matching caregivers | Google Gemini | Only if docs complete + home assessment done |
| **Agent 3: Scheduling** | Creates scheduling recommendation | Google Gemini | Always runs |

---

### 2. Journey Board Flow

**Endpoints:** 
- `GET /api/v1/journey/board` - Get all referrals by stage
- `POST /api/v1/referrals/{id}/journey/advance` - Advance to next stage

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                            JOURNEY STAGES                                       │
├──────────┬───────────┬───────────┬──────────┬──────────┬──────────┬───────────┤
│ INTAKE   │ DOCS      │ INSURANCE │ HOME     │ CAREGIVER│ SCHEDULED│ SERVICE   │
│ RECEIVED │ COMPLETED │ VERIFIED  │ ASSESSED │ MATCHED  │          │ COMPLETED │
├──────────┼───────────┼───────────┼──────────┼──────────┼──────────┼───────────┤
│    ──────▶──────────▶───────────▶──────────▶──────────▶──────────▶           │
│          │           │           │          │          │          │           │
│          │ Updates:  │           │ Updates: │          │          │           │
│          │ docs_     │           │ home_    │          │          │           │
│          │ complete  │           │ assess   │          │          │           │
│          │ = 'Y'     │           │ = 'Y'    │          │          │           │
└──────────┴───────────┴───────────┴──────────┴──────────┴──────────┴───────────┘
                                         │
                                         ▼
                              📧 Email Notification Sent
                                  on each advance
```

#### Stage Side Effects:

| Stage | Database Updates | Triggers |
|-------|-----------------|----------|
| `DOCS_COMPLETED` | `docs_complete = 'Y'` | Email notification |
| `HOME_ASSESSMENT_COMPLETED` | `home_assessment_done = 'Y'` | Email notification |
| `READY_TO_BILL` | `ready_to_bill = 'Y'` | Email notification |
| `SERVICE_COMPLETED` | `service_complete = 'Y'`, `schedule_status = 'COMPLETED'` | Email notification |

---

### 3. Schedule Confirmation Flow

**Endpoint:** `POST /api/v1/schedule/confirm`

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────┐
│  Frontend   │────▶│  Validate       │────▶│  Update DB      │────▶│ Send Email  │
│  Confirm    │     │  - Referral     │     │  - schedule_    │     │ Confirmation│
│  Button     │     │  - Caregiver    │     │    status       │     │             │
└─────────────┘     └─────────────────┘     │  - assigned_    │     └─────────────┘
                                            │    caregiver    │
                                            └─────────────────┘
```

---

## File Structure

```
backend/
├── app.py                          # Main FastAPI application (2947 lines)
├── requirements.txt                # Python dependencies
├── .env                            # Environment variables
├── ARCHITECTURE.md                 # This document
│
├── config/
│   └── agent_config.yaml           # Agent scoring weights & thresholds
│
├── database/
│   ├── db_service.py               # PostgreSQL connection & queries
│   ├── schema.sql                  # Database schema
│   └── migrations/                 # Database migrations
│       └── 001_add_journey_stage.sql
│
├── src/
│   ├── models/
│   │   ├── schemas.py              # API request/response models
│   │   └── data_schemas.py         # Data transfer objects
│   │
│   └── services/
│       ├── agent_workflow.py       # 3-Agent AI Workflow (Gemini)
│       ├── crew_workflow.py        # CrewAI Multi-Agent
│       ├── email_service.py        # Gmail SMTP notifications
│       ├── landingai_service.py    # Document OCR/extraction
│       ├── faiss_service.py        # Vector similarity search
│       ├── rules_engine.py         # Business rule validation
│       └── sorting_agent.py        # Priority sorting
│
└── data/
    ├── referrals_synthetic.csv     # Sample referral data
    └── caregivers_synthetic.csv    # Sample caregiver data
```

---

## API Endpoints Reference

### Referrals
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/referrals` | List all referrals |
| POST | `/api/v1/intake/simulate` | Simulate new referral intake |
| POST | `/api/v1/intake/from-pdf` | Create referral from PDF document |

### Journey
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/journey/board` | Get journey board with referrals by stage |
| GET | `/api/v1/referrals/{id}/journey` | Get journey history for referral |
| POST | `/api/v1/referrals/{id}/journey/advance` | Advance referral to next stage |

### AI Agents
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/agent/process-referral` | Process referral through 3-agent workflow |
| GET | `/api/v1/agent/pending-referrals` | Get referrals pending scheduling |
| POST | `/api/v1/agent/reload-rules` | Reload business rules |

### Scheduling
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/scheduling/apply` | Apply scheduling recommendation |
| POST | `/api/v1/schedule/confirm` | Confirm and finalize schedule |

### Caregivers
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/caregivers` | List all caregivers |

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/dashboard-metrics` | Get dashboard KPI metrics |
| GET | `/api/v1/ops/summary` | Get operations summary |
| GET | `/api/v1/stats` | Get system statistics |

### Notifications
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/email/send-notification` | Send email notification |

### Document Processing
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/process-image` | Process image with Landing AI |
| POST | `/api/v1/upload-image` | Upload and process image file |

---

## Environment Variables

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=healthops_db
DB_USER=postgres
DB_PASSWORD=your_password

# AI Services
GOOGLE_API_KEY=your_gemini_api_key        # Google Gemini for AI agents
LANDING_AI_API_KEY=your_landingai_key     # Document OCR

# Email Notifications
SENDER_EMAIL=your_email@gmail.com
DEFAULT_RECEIVER_EMAIL=receiver@email.com
GMAIL_APP_PASSWORD=your_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Agent Configuration
AGENT_CONFIG_PATH=config/agent_config.yaml

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True
```

---

## Database Schema

### referrals table
```sql
CREATE TABLE referrals (
    referral_id VARCHAR(20) PRIMARY KEY,
    patient_name VARCHAR(100),
    patient_city VARCHAR(50),
    service_type VARCHAR(50),
    urgency VARCHAR(20),
    auth_status VARCHAR(20),
    docs_complete CHAR(1) DEFAULT 'N',
    home_assessment_done CHAR(1) DEFAULT 'N',
    schedule_status VARCHAR(30),
    assigned_caregiver_id VARCHAR(20),
    journey_stage VARCHAR(50) DEFAULT 'INTAKE_RECEIVED',
    journey_updated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### caregivers table
```sql
CREATE TABLE caregivers (
    caregiver_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100),
    city VARCHAR(50),
    skills TEXT,
    availability VARCHAR(50),
    status VARCHAR(20) DEFAULT 'ACTIVE'
);
```

---

## Data Flow Summary

```
User Action → API Endpoint → Service Layer → Database/AI → Response → UI Update
                                   │
                                   └──→ Email Notification (optional)
```

---

## Running the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

Access API docs: http://localhost:8000/docs

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | FastAPI |
| Database | PostgreSQL |
| AI | Google Gemini (gemini-2.0-flash) |
| Email | Gmail SMTP |
| OCR | Landing AI |
| Vector Search | FAISS |
| Multi-Agent | CrewAI (optional) |
