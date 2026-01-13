# HealthOps AI Agent Instructions

## Architecture Overview

**HealthOps** is an agentic referral management system with dual operation modes:
- **Database mode**: PostgreSQL backend with 1,000+ synthetic referrals and 300+ caregivers
- **File mode** (demo): JSON-based persistence (`data/*_runtime.json`, `data/*_overrides.json`) - **excluded from git**

**Critical**: The system auto-detects mode on startup. File mode triggers **autopilot** - automatic stage progression that runs on READ endpoints (e.g., `GET /api/v1/referrals`). This is intentional demo behavior, not a bug.

### Stack
- **Backend**: FastAPI (Python), port 8022, runs with `uvicorn app:app --reload --port 8022`
- **Frontend**: React 19 + TypeScript, port 3000, runs with `npm start`
- **AI Integrations**: LandingAI (PDF parsing), OpenAI/Swarms (agent workflows)

## Key Workflows

### 1. PDF Intake → Referral Creation
When PDFs are uploaded via `/api/v1/intake/from-pdf`:
1. LandingAI extracts text/tables
2. Heuristic classifier determines type (referral/compliance/other) - see `_classify_document()` in `app.py`
3. **Referral**: Creates new referral, triggers autopilot if file mode
4. **Compliance**: Saves to `data/compliance_runtime.json` as guardrail
5. **Other**: Ignored with confidence score

### 2. Autopilot Stage Progression (File Mode Only)
In `app.py`, functions like `_autopilot_tick_for_referral()` auto-advance stages:
```python
INTAKE_RECEIVED → DOCS_COMPLETED → HOME_ASSESSMENT → SCHEDULED → READY_TO_BILL → SERVICE_COMPLETED
```
Runs on GET endpoints (`/api/v1/referrals`, `/api/v1/ops/summary`, `/api/v1/journey/board`) with probabilistic advancement. This simulates real-world progression for demos.

### 3. Journey Timeline System
Each referral has a timeline in `data/journey_overrides.json`:
```json
{
  "REF-1001": {
    "stage": "SCHEDULED",
    "timeline": [
      {"stage": "INTAKE_RECEIVED", "at": "2026-01-10T10:00:00", "source": "system"},
      {"stage": "SCHEDULED", "at": "2026-01-11T14:30:00", "source": "scheduler", "note": "Assigned CG-123"}
    ]
  }
}
```
Scheduling from AI Scheduler tab records journey events via `_record_journey_event()`.

## Configuration: Zero Hardcoding

**All** agent thresholds/weights are in `backend/config/agent_config.yaml`:
- Validation scoring: insurance penalties, passing threshold (70)
- Matching scoring: city/skill match points (40/40/20/20/10)
- Scheduling limits: max units/week (20), max pending (50)

Frontend config in `frontend/src/config/agentUiConfig.ts`: status colors, action keywords, priority mappings.

See `backend/HARDCODING_REMOVAL_SUMMARY.md` for complete removal audit.

## Data Coordination

### Frontend State Management
`App.tsx` uses `dataVersion` counter + `onDataChanged()` callback to coordinate refreshes across tabs:
- Scheduling applies → increment `dataVersion` → all tabs (Referrals, Caregivers, Journey) reload
- Pattern: `<AgentScheduler dataVersion={dataVersion} onDataChanged={handleDataChanged} />`

### API Base URL
Both `api.ts` and `agentService.ts` use `http://127.0.0.1:8022` (not `localhost:8000`). Backend must run on port 8022.

## Component Patterns

### Modal Pattern (Journey/Scheduling)
`ReferralJourneyModal.tsx` demonstrates the portal pattern:
- Overlay with `position: fixed; z-index: 1000`
- Click-outside-to-close via `onClick={onClose}` on overlay, `onClick={(e) => e.stopPropagation()}` on modal
- Stage advancement buttons filtered: no manual "SCHEDULED" (done via Scheduler tab)

### Tabbed Navigation
6 tabs in `App.tsx`: Referrals, Caregivers, AI Scheduler, Journey Board, PDF Intake, Compliance. Journey Board is kanban-style stage grouping; PDF Intake handles LandingAI uploads.

## Git Workflow

**Important**: Runtime JSON files must stay excluded:
- `.gitignore` includes `data/*runtime*.json` and `data/*overrides*.json`
- If staging shows these files, unstage: `git restore --staged data/*.json`
- When rebasing, resolve conflicts in `backend/app.py`, `AgentScheduler.tsx`, `api.ts` by merging features (keep resilient LandingAI init + crew_workflow from main, keep autopilot + journey system from feature branch)

## Running the System

```bash
# Backend (from project root)
cd backend && uvicorn app:app --reload --port 8022

# Frontend (separate terminal)
cd frontend && npm start

# Database setup (optional, falls back to file mode)
cd backend && python setup_database.py
```

LandingAI and OpenAI keys optional; system gracefully degrades without them.

## Common Gotchas

1. **Autopilot runs on GET**: Not a bug - file mode intentionally progresses stages to simulate activity
2. **Port mismatch**: Backend must be 8022, frontend expects this in `API_BASE_URL`
3. **File mode vs DB mode**: Check `backend/app.py` startup logs - "Database connection failed" means file mode active
4. **Journey timeline**: Only records events from Scheduler tab or manual advancement, not autopilot ticks
5. **Compliance docs**: PDFs classified as "compliance" go to dedicated store, not referral pipeline
