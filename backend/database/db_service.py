import os
import psycopg2
from psycopg2 import pool, sql
import csv
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv


class ConfigLoader:
    
    def __init__(self, env_path: str = None):
        if env_path is None:
            current_dir = Path(__file__).parent.parent
            env_path = current_dir / ".env"
        self.env_path = env_path
        self._load_env()
    
    def _load_env(self):
        load_dotenv(self.env_path)
    
    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        return os.getenv(key, default)


class DatabaseService:
    _connection_pool = None
    
    def __init__(self):
        self.config = ConfigLoader()
        self.connection = None
        self.cursor = None
        self._load_db_config()
        self._init_pool()
    
    def _load_db_config(self):
        self.db_host = self.config.get("DB_HOST", "localhost")
        self.db_port = self.config.get("DB_PORT", "5432")
        self.db_name = self.config.get("DB_NAME", "healthops_db")
        self.db_user = self.config.get("DB_USER", "postgres")
        self.db_password = self.config.get("DB_PASSWORD", "")
    
    def _init_pool(self):
        """Initialize connection pool for better performance"""
        if DatabaseService._connection_pool is None:
            try:
                DatabaseService._connection_pool = psycopg2.pool.SimpleConnectionPool(
                    1,  # minconn
                    10,  # maxconn
                    host=self.db_host,
                    port=self.db_port,
                    database=self.db_name,
                    user=self.db_user,
                    password=self.db_password
                )
            except Exception as e:
                print(f"Failed to create connection pool: {e}")
    
    def connect(self) -> Dict[str, Any]:
        try:
            if DatabaseService._connection_pool:
                self.connection = DatabaseService._connection_pool.getconn()
            else:
                self.connection = psycopg2.connect(
                    host=self.db_host,
                    port=self.db_port,
                    database=self.db_name,
                    user=self.db_user,
                    password=self.db_password
                )
            self.cursor = self.connection.cursor()
            
            return {
                "success": True,
                "message": f"Connected to database: {self.db_name}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}"
            }
    
    def disconnect(self):
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.connection:
            if DatabaseService._connection_pool:
                DatabaseService._connection_pool.putconn(self.connection)
            else:
                self.connection.close()
            self.connection = None
    
    def execute_sql_file(self, sql_file_path: str) -> Dict[str, Any]:
        try:
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            self.cursor.execute(sql_script)
            self.connection.commit()
            
            return {
                "success": True,
                "message": f"Executed SQL file: {sql_file_path}"
            }
            
        except Exception as e:
            self.connection.rollback()
            return {
                "success": False,
                "message": f"SQL execution failed: {str(e)}"
            }
    
    def create_schema(self) -> Dict[str, Any]:
        schema_path = Path(__file__).parent / "schema.sql"
        return self.execute_sql_file(str(schema_path))
    
    def import_csv_to_table(
        self, 
        csv_file_path: str,
        table_name: str,
        columns: List[str] = None
    ) -> Dict[str, Any]:
        try:
            csv_path = Path(csv_file_path)
            
            if not csv_path.exists():
                return {
                    "success": False,
                    "message": f"CSV file not found: {csv_file_path}"
                }
            
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                if columns is None:
                    columns = reader.fieldnames
                
                records = list(reader)
                
                if not records:
                    return {
                        "success": False,
                        "message": "No data found in CSV"
                    }
                
                placeholders = ','.join(['%s'] * len(columns))
                insert_query = f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"
                
                for record in records:
                    values = [record.get(col, None) for col in columns]
                    values = [None if v == '' else v for v in values]
                    
                    self.cursor.execute(insert_query, values)
                
                self.connection.commit()
                
                return {
                    "success": True,
                    "message": f"Imported {len(records)} records into {table_name}",
                    "records_imported": len(records)
                }
                
        except Exception as e:
            self.connection.rollback()
            return {
                "success": False,
                "message": f"Import failed: {str(e)}"
            }
    
    def import_caregivers(self, csv_path: str = None) -> Dict[str, Any]:
        if csv_path is None:
            csv_path = Path(__file__).parent.parent.parent / "data" / "caregivers_synthetic.csv"
        
        columns = [
            'caregiver_id', 'gender', 'date_of_birth', 'age',
            'primary_language', 'skills', 'employment_type',
            'availability', 'city', 'active'
        ]
        
        return self.import_csv_to_table(str(csv_path), 'caregivers', columns)
    
    def import_referrals(self, csv_path: str = None) -> Dict[str, Any]:
        if csv_path is None:
            csv_path = Path(__file__).parent.parent.parent / "data" / "referrals_synthetic.csv"
        
        columns = [
            'referral_id', 'use_case', 'service_type', 'referral_source',
            'urgency', 'referral_received_date', 'first_outreach_date',
            'last_activity_date', 'insurance_active', 'payer', 'plan_type',
            'auth_required', 'auth_status', 'auth_start_date', 'auth_end_date',
            'auth_units_total', 'auth_units_remaining', 'unit_type',
            'docs_complete', 'home_assessment_done', 'patient_responsive',
            'contact_attempts', 'schedule_status', 'scheduled_date',
            'units_scheduled_next_7d', 'units_delivered_to_date',
            'service_complete', 'evv_or_visit_note_exists', 'ready_to_bill',
            'claim_status', 'denial_reason', 'payment_amount', 'patient_dob',
            'patient_age', 'patient_gender', 'patient_address', 'patient_city',
            'patient_zip', 'agent_segment', 'agent_next_action', 'agent_rationale'
        ]
        
        return self.import_csv_to_table(str(csv_path), 'referrals', columns)
    
    def query(self, sql_query: str, params: tuple = None) -> Dict[str, Any]:
        try:
            # Ensure we have a connection
            if not self.connection or not self.cursor:
                conn_result = self.connect()
                if not conn_result.get("success"):
                    return {
                        "success": False,
                        "message": conn_result.get("message", "Database connection failed")
                    }
            
            self.cursor.execute(sql_query, params)
            
            if sql_query.strip().upper().startswith('SELECT'):
                results = self.cursor.fetchall()
                columns = [desc[0] for desc in self.cursor.description]
                
                data = [dict(zip(columns, row)) for row in results]
                
                return {
                    "success": True,
                    "data": data,
                    "row_count": len(data)
                }
            else:
                self.connection.commit()
                return {
                    "success": True,
                    "message": "Query executed successfully",
                    "rows_affected": self.cursor.rowcount
                }
                
        except Exception as e:
            if self.connection:
                try:
                    self.connection.rollback()
                except Exception:
                    pass
            return {
                "success": False,
                "message": f"Query failed: {str(e)}"
            }
    
    def get_table_stats(self) -> Dict[str, Any]:
        stats = {}
        
        try:
            self.cursor.execute("SELECT COUNT(*) FROM referrals")
            stats['total_referrals'] = self.cursor.fetchone()[0]
            
            self.cursor.execute("SELECT COUNT(*) FROM caregivers")
            stats['total_caregivers'] = self.cursor.fetchone()[0]
            
            self.cursor.execute("SELECT COUNT(*) FROM caregivers WHERE active = 'Y'")
            stats['active_caregivers'] = self.cursor.fetchone()[0]
            
            self.cursor.execute("SELECT COUNT(*) FROM referrals WHERE service_complete = 'N'")
            stats['active_referrals'] = self.cursor.fetchone()[0]
            
            return {
                "success": True,
                "stats": stats
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get stats: {str(e)}"
            }


if __name__ == "__main__":
    db = DatabaseService()
    
    print("Connecting to database...")
    result = db.connect()
    print(result)
    
    if result['success']:
        print("\nCreating schema...")
        result = db.create_schema()
        print(result)
        
        print("\nImporting caregivers...")
        result = db.import_caregivers()
        print(result)
        
        print("\nImporting referrals...")
        result = db.import_referrals()
        print(result)
        
        print("\nGetting table statistics...")
        result = db.get_table_stats()
        print(result)
        
        db.disconnect()
