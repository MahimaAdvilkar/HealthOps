# PostgreSQL Database Setup Guide

## Overview
This guide helps you set up PostgreSQL database for HealthOps with referrals and caregivers data.

## Prerequisites
1. Install PostgreSQL: https://www.postgresql.org/download/windows/
2. During installation, note down your postgres password

## Setup Steps

### 1. Install PostgreSQL Python Driver
```bash
cd backend
pip install psycopg2-binary
```

### 2. Configure Database Connection
Update `backend/.env` with your PostgreSQL credentials:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=healthops_db
DB_USER=postgres
DB_PASSWORD=your_password_here
```

### 3. Create Database

#### Option A: Using psql Command Line
```bash
# Open PowerShell and connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE healthops_db;

# Exit psql
\q
```

#### Option B: Using pgAdmin
1. Open pgAdmin 4
2. Right-click on "Databases" → Create → Database
3. Name: `healthops_db`
4. Click Save

### 4. Create Tables and Import Data

#### Option A: Using Python Service (Recommended)
```bash
cd backend
python database/db_service.py
```

This will:
- Create all tables (referrals, caregivers)
- Create indexes for performance
- Create views for common queries
- Import CSV data automatically

#### Option B: Using SQL Files Manually
```bash
# Create schema
psql -U postgres -d healthops_db -f database/schema.sql

# Import data
psql -U postgres -d healthops_db -f database/import_data.sql
```

## Database Schema

### Referrals Table
- **Primary Key**: referral_id
- **Columns**: 40+ fields including patient info, insurance, authorization, scheduling
- **Indexes**: On city, urgency, segment, status, payer

### Caregivers Table
- **Primary Key**: caregiver_id
- **Columns**: demographics, skills, availability, location
- **Indexes**: On city, active status, skills, language

## Useful Views

### active_referrals
Shows all referrals requiring action
```sql
SELECT * FROM active_referrals;
```

### available_caregivers
Lists all active caregivers by city and skills
```sql
SELECT * FROM available_caregivers WHERE city = 'San Francisco';
```

### pending_scheduling
Referrals awaiting scheduling
```sql
SELECT * FROM pending_scheduling WHERE urgency = 'Urgent';
```

### ready_for_billing
Referrals ready to be billed
```sql
SELECT * FROM ready_for_billing WHERE payer = 'Cigna';
```

## Using the Database Service in Code

```python
from database.db_service import DatabaseService

# Initialize service
db = DatabaseService()

# Connect
result = db.connect()
if result['success']:
    
    # Query active caregivers
    result = db.query("""
        SELECT * FROM caregivers 
        WHERE active = 'Y' AND city = %s
    """, ('San Francisco',))
    
    caregivers = result['data']
    
    # Get statistics
    stats = db.get_table_stats()
    print(stats)
    
    # Close connection
    db.disconnect()
```

## Sample Queries

### Find urgent referrals needing scheduling
```sql
SELECT 
    referral_id,
    service_type,
    patient_city,
    auth_end_date,
    contact_attempts
FROM referrals
WHERE urgency = 'Urgent'
  AND schedule_status = 'NOT_SCHEDULED'
  AND insurance_active = 'Y'
ORDER BY auth_end_date;
```

### Match caregivers to referrals by city and skills
```sql
SELECT 
    r.referral_id,
    r.service_type,
    r.patient_city,
    c.caregiver_id,
    c.skills,
    c.availability
FROM referrals r
INNER JOIN caregivers c ON r.patient_city = c.city
WHERE r.schedule_status = 'NOT_SCHEDULED'
  AND c.active = 'Y'
  AND c.skills LIKE '%' || r.use_case || '%'
LIMIT 10;
```

### Get billing summary by payer
```sql
SELECT 
    payer,
    COUNT(*) as total_referrals,
    SUM(units_delivered_to_date) as total_units,
    SUM(payment_amount) as total_revenue,
    COUNT(CASE WHEN claim_status = 'PAID' THEN 1 END) as paid_claims
FROM referrals
WHERE ready_to_bill = 'Y'
GROUP BY payer
ORDER BY total_revenue DESC;
```

## Troubleshooting

### Connection Issues
- Ensure PostgreSQL service is running
- Check firewall settings for port 5432
- Verify credentials in `.env` file

### Import Errors
- Check CSV file paths are correct
- Ensure CSV files have headers
- Verify date formats (YYYY-MM-DD)

### Permission Issues
```sql
-- Grant permissions to user
GRANT ALL PRIVILEGES ON DATABASE healthops_db TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
```

## Data Statistics
- **Referrals**: ~1,000 records
- **Caregivers**: ~300 records
- **Total Storage**: ~2-3 MB

## Next Steps
1. Install psycopg2: `pip install psycopg2-binary`
2. Update `.env` with your database password
3. Run: `python database/db_service.py`
4. Verify data: Check tables in pgAdmin or run sample queries
