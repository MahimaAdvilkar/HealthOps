# HealthOps Frontend - Referrals & Caregivers Dashboard

## Overview
React-based dashboard to display and manage referrals and caregivers data from PostgreSQL database.

## Features

### Dashboard Stats
- Total Referrals: 1,000
- Active Referrals: 684
- Total Caregivers: 300
- Active Caregivers: 226

### Referrals Table
- View all 1,000 referrals from PostgreSQL
- Filter by:
  - Urgency (Urgent/Routine)
  - Agent Segment (RED/ORANGE/GREEN)
  - Schedule Status
- Display columns:
  - Referral ID
  - Service Type
  - Urgency (color-coded badges)
  - Agent Segment (color-coded badges)
  - Patient City
  - Payer
  - Schedule Status
  - Units Remaining
  - Next Action
  - Contact Attempts

### Caregivers Table
- View all 300 caregivers from PostgreSQL
- Filter by:
  - City
  - Active Status (Y/N)
  - Skills
- Display columns:
  - Caregiver ID
  - Gender
  - Age
  - Primary Language
  - Skills
  - Employment Type
  - Availability
  - City
  - Status (Active/Inactive badge)

## Tech Stack

### Frontend
- React 19.2.3
- TypeScript 4.9.5
- CSS3 for styling

### Backend
- FastAPI
- PostgreSQL 18
- psycopg2-binary

## Running the Application

### 1. Start Backend Server
```bash
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Backend will run at: http://localhost:8000

### 2. Start Frontend Server
```bash
cd frontend
npm start
```

Frontend will run at: http://localhost:3000

## API Endpoints

### GET /api/v1/referrals
Fetch referrals with optional filters:
- `limit` - Number of records (default: 100, max: 1000)
- `offset` - Pagination offset
- `urgency` - Filter by urgency (Urgent/Routine)
- `agent_segment` - Filter by segment (RED/ORANGE/GREEN)
- `schedule_status` - Filter by status

Example:
```
GET http://localhost:8000/api/v1/referrals?urgency=Urgent&limit=50
```

### GET /api/v1/caregivers
Fetch caregivers with optional filters:
- `limit` - Number of records (default: 100, max: 500)
- `offset` - Pagination offset
- `city` - Filter by city
- `active` - Filter by status (Y/N)
- `skills` - Filter by skills (partial match)

Example:
```
GET http://localhost:8000/api/v1/caregivers?city=San Francisco&active=Y
```

### GET /api/v1/stats
Get database statistics:
```json
{
  "total_referrals": 1000,
  "active_referrals": 684,
  "total_caregivers": 300,
  "active_caregivers": 226
}
```

## Current Status

✅ Backend API running on port 8000
✅ Frontend React app running on port 3000
✅ PostgreSQL database connected
✅ 1,000 referrals loaded
✅ 300 caregivers loaded

## Access the Dashboard

Open your browser and go to:
**http://localhost:3000**

You'll see:
1. **Statistics Cards** at the top showing totals
2. **Tab Navigation** to switch between Referrals and Caregivers
3. **Filters** to narrow down data
4. **Tables** displaying all your CSV data from PostgreSQL

## Color Coding

### Urgency
- 🔴 Red Badge = Urgent
- 🟢 Green Badge = Routine

### Agent Segment
- 🔴 Red Badge = RED segment
- 🟠 Orange Badge = ORANGE segment
- 🟢 Green Badge = GREEN segment

### Caregiver Status
- 🟢 Green Badge = Active
- ⚫ Gray Badge = Inactive

## Data Source
All data is loaded from:
- `data/referrals_synthetic.csv` → PostgreSQL `referrals` table
- `data/caregivers_synthetic.csv` → PostgreSQL `caregivers` table

## Troubleshooting

### Backend Issues
```bash
# Check if backend is running
curl http://localhost:8000

# Expected: {"message":"HealthOps API - Landing AI Image Processing",...}
```

### Frontend Issues
```bash
# Clear cache and restart
cd frontend
rm -rf node_modules/.cache
npm start
```

### Database Issues
```bash
# Verify database connection
cd backend
python -c "from database.db_service import DatabaseService; db = DatabaseService(); print(db.connect())"
```

## Next Steps
- Add pagination to tables
- Add export to CSV functionality
- Add detailed view for individual referrals/caregivers
- Add charts and visualizations
- Add search functionality
