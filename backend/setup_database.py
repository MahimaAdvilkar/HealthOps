# Quick Setup Script for PostgreSQL Database
# Make sure to update DB_PASSWORD in .env file first!

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_service import DatabaseService

def main():
    print("=" * 60)
    print("HealthOps Database Setup")
    print("=" * 60)
    
    db = DatabaseService()
    
    # Step 1: Connect
    print("\n1. Connecting to PostgreSQL...")
    result = db.connect()
    print(f"   {result['message']}")
    
    if not result['success']:
        print("\nConnection failed!")
        print("\nPlease check:")
        print("1. PostgreSQL service is running (it is ✓)")
        print("2. DB_PASSWORD in .env matches your PostgreSQL password")
        print("3. Database user 'postgres' exists")
        return
    
    # Step 2: Create Schema
    print("\n2. Creating database schema...")
    result = db.create_schema()
    if result['success']:
        print("   ✓ Tables created successfully")
    else:
        print(f"   ⚠ {result['message']}")
    
    # Step 3: Import Caregivers
    print("\n3. Importing caregivers data...")
    result = db.import_caregivers()
    if result['success']:
        print(f"   ✓ Imported {result['records_imported']} caregivers")
    else:
        print(f"   ✗ {result['message']}")
    
    # Step 4: Import Referrals
    print("\n4. Importing referrals data...")
    result = db.import_referrals()
    if result['success']:
        print(f"   ✓ Imported {result['records_imported']} referrals")
    else:
        print(f"   ✗ {result['message']}")
    
    # Step 5: Get Statistics
    print("\n5. Database Statistics:")
    result = db.get_table_stats()
    if result['success']:
        stats = result['stats']
        print(f"   Total Referrals:     {stats['referrals_count']}")
        print(f"   Active Referrals:    {stats['active_referrals']}")
        print(f"   Total Caregivers:    {stats['caregivers_count']}")
        print(f"   Active Caregivers:   {stats['active_caregivers']}")
    
    db.disconnect()
    
    print("\n" + "=" * 60)
    print("✓ Database setup completed successfully!")
    print("=" * 60)
    print("\nYou can now use the database in your application.")
    print("\nQuick test query:")
    print("  SELECT * FROM active_referrals LIMIT 5;")

if __name__ == "__main__":
    main()
