# HealthOps Backend - Simple Flow & Usage

## What is HealthOps?
HealthOps is a healthcare backend system that uses AI agents to:
- Validate and process referrals (check insurance, docs, etc.)
- Match caregivers to clients based on skills and location
- Schedule appointments and manage workflow status
- Send email notifications for important events

All agent logic (scoring, thresholds, limits) is configured in YAML and .env files—no hardcoded values.

---

## How the Backend Works (Step-by-Step)

1. **User interacts with the dashboard (frontend)**
2. **Frontend calls backend API endpoints** to:
   - List referrals and caregivers
   - Process and schedule referrals
   - Track journey and compliance
3. **Backend loads data** from CSV files or the database
4. **AI agents** validate, match, and schedule using config-driven logic
5. **Email notifications** are sent for key events (using Gmail SMTP)

---

## How to Use

1. **Start the backend:**
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app:app --reload --port 8000
   ```
2. **Start the frontend and use the dashboard**
3. **APIs are available at** `http://localhost:8000` (see API docs at `/docs`)

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
- See `CONFIGURATION.md` for full details

---

## Need help?
- See `CONFIGURATION.md` and `HARDCODING_REMOVAL_SUMMARY.md` for more info
