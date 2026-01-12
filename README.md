# HealthOps - Full System Overview & Usage

## What is HealthOps?
HealthOps is a healthcare operations platform that uses AI agents to automate and optimize the referral and caregiver management process. It consists of a backend (FastAPI, Python) and a frontend (React) dashboard.

---

## Key Features
- **AI-driven referral validation**: Checks insurance, documentation, and readiness for each referral.
- **Caregiver matching**: Finds the best caregiver for each client based on skills, location, and availability.
- **Automated scheduling**: Schedules appointments and manages workflow status.
- **Email notifications**: Sends notifications for important workflow events (using Gmail SMTP).
- **Configurable logic**: All agent scoring, thresholds, and limits are set in YAML and .env files—no hardcoded values.
- **Frontend dashboard**: Visualizes referrals, caregivers, scheduling, and compliance.

---

## System Architecture
- **Backend**: FastAPI app (Python) with modular AI agent workflow, database/CSV data, and REST API endpoints.
- **Frontend**: React dashboard (TypeScript) for managing and visualizing referrals, caregivers, and workflow.
- **Configuration**: All agent logic is externalized to YAML (`backend/config/agent_config.yaml`) and environment variables (`backend/.env`).

---

## How the System Works (Step-by-Step)
1. **User interacts with the dashboard (frontend)**
2. **Frontend calls backend API endpoints** to:
   - List referrals and caregivers
   - Process and schedule referrals
   - Track journey and compliance
3. **Backend loads data** from CSV files or the database
4. **AI agents** validate, match, and schedule using config-driven logic
5. **Email notifications** are sent for key events (using Gmail SMTP)

---

## Quick Start

### Backend
1. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
2. Start the backend server:
   ```bash
   uvicorn app:app --reload --port 8000
   ```
3. API docs available at: `http://localhost:8000/docs`

### Frontend
1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```
2. Start the frontend:
   ```bash
   npm start
   ```
3. Open the dashboard at: `http://localhost:3000`

---

## Configuration
- **Agent logic:** `backend/config/agent_config.yaml`
- **Environment variables:** `backend/.env`
- **Email notifications:** Uses your Gmail SMTP config

Example `.env`:
```
SENDER_EMAIL=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

---

## Developer Notes
- All agent scoring, thresholds, and limits are in YAML config
- No hardcoded values in the agent workflow
- See `backend/CONFIGURATION.md` for full details
- See `backend/HARDCODING_REMOVAL_SUMMARY.md` for hardcoding removal summary

---

## Need help?
- See `backend/CONFIGURATION.md` and `backend/HARDCODING_REMOVAL_SUMMARY.md` for more info
- For architecture, see `backend/ARCHITECTURE.md`
