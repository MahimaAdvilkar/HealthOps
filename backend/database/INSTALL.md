# PostgreSQL Installation and Setup for HealthOps

## Step 1: Install PostgreSQL

### Download PostgreSQL for Windows
1. Go to: https://www.postgresql.org/download/windows/
2. Click "Download the installer" (from EDB)
3. Download PostgreSQL 16.x for Windows x86-64

### Installation Steps
1. Run the installer
2. **Important**: During installation, set a password for the postgres user (remember this!)
3. Keep default port: 5432
4. Select components:
   - PostgreSQL Server ✓
   - pgAdmin 4 ✓
   - Command Line Tools ✓
5. Complete installation

## Step 2: Update Environment Configuration

After installation, update `backend/.env` with your PostgreSQL password:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=healthops_db
DB_USER=postgres
DB_PASSWORD=YOUR_PASSWORD_HERE  # Replace with password you set during installation
```

## Step 3: Create Database

### Option A: Using pgAdmin (Graphical Interface)
1. Open pgAdmin 4 from Start Menu
2. Connect using your postgres password
3. Right-click "Databases" → Create → Database
4. Database name: `healthops_db`
5. Click Save

### Option B: Using PowerShell (After adding PostgreSQL to PATH)
```powershell
# Add PostgreSQL to PATH (replace with your PostgreSQL version)
$env:Path += ";C:\Program Files\PostgreSQL\16\bin"

# Create database
psql -U postgres -c "CREATE DATABASE healthops_db;"
```

## Step 4: Setup Tables and Import Data

Once PostgreSQL is installed and database is created:

```powershell
cd C:\projects\HealthOps\backend

# Run the setup script
python database/db_service.py
```

This will:
- ✓ Connect to PostgreSQL
- ✓ Create tables (referrals, caregivers)
- ✓ Create indexes for performance
- ✓ Create useful views
- ✓ Import all CSV data automatically
- ✓ Show statistics

## Alternative: Manual SQL Import

If you prefer to run SQL files manually using pgAdmin:

1. Open pgAdmin 4
2. Connect to `healthops_db`
3. Click Tools → Query Tool
4. Open and run `backend/database/schema.sql`
5. Then open and run `backend/database/import_data.sql`
   (Update file paths in import_data.sql to match your system)

## Verify Installation

After setup, verify your data:

```python
# In Python
from database.db_service import DatabaseService

db = DatabaseService()
result = db.connect()
print(result)

stats = db.get_table_stats()
print(stats)
# Should show:
# - referrals_count: ~1000
# - caregivers_count: ~300
# - active_caregivers: ~200+
# - active_referrals: ~800+

db.disconnect()
```

Or using SQL in pgAdmin:

```sql
SELECT COUNT(*) FROM referrals;
SELECT COUNT(*) FROM caregivers;
SELECT * FROM active_referrals LIMIT 10;
SELECT * FROM available_caregivers LIMIT 10;
```

## Quick Reference

### Start PostgreSQL Service (if needed)
```powershell
# Check if service is running
Get-Service postgresql*

# Start service if stopped
Start-Service postgresql-x64-16  # Replace with your version
```

### Connection String
```
postgresql://postgres:YOUR_PASSWORD@localhost:5432/healthops_db
```

## What You Get

✓ **1,000+ Referral Records** with patient data, insurance, scheduling info
✓ **300+ Caregiver Records** with skills, availability, location
✓ **Optimized Indexes** for fast queries
✓ **4 Useful Views** for common queries
✓ **Python Service** for easy database operations

## Next Steps After Installation

1. Download PostgreSQL installer
2. Install with password
3. Update `.env` with your password
4. Run `python database/db_service.py`
5. Verify data is loaded
