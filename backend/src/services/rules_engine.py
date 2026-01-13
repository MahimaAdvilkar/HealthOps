"""
Rules Engine for AI Agent Scheduler
Converts natural language rules to SQL WHERE clauses using LLM
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv

try:
    import google.generativeai as genai
except ModuleNotFoundError:
    genai = None

load_dotenv()


class SchedulerRulesEngine:
    """
    Reads rules from text file and converts them to SQL WHERE clauses
    Uses Google Gemini LLM to intelligently parse natural language rules
    """
    
    def __init__(self, rules_file_path: str = None):
        if rules_file_path is None:
            # Go up from src/services to backend, then to config
            rules_file_path = Path(__file__).parent.parent.parent / "config" / "scheduler_rules.txt"
        
        self.rules_file_path = rules_file_path
        self.rules_text = self._load_rules()
        self.model = self._initialize_llm()
        
    def _load_rules(self) -> str:
        """Load rules from text file"""
        try:
            with open(self.rules_file_path, 'r') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading rules file: {e}")
            return ""
    
    def _initialize_llm(self):
        """Initialize Google Gemini client"""
        if genai is None:
            print("WARNING: google-generativeai not installed. AI features will use fallback.")
            return None

        google_api_key = os.getenv('GOOGLE_API_KEY')
        
        if not google_api_key or google_api_key == 'your_google_api_key_here':
            print("WARNING: GOOGLE_API_KEY not set. AI features will use fallback.")
            return None
        
        genai.configure(api_key=google_api_key)
        return genai.GenerativeModel('gemini-2.0-flash')
    
    def generate_sql_where_clause(self) -> Dict[str, Any]:
        """
        Convert rules to SQL WHERE clause using LLM
        Note: ORDER BY is now handled by the AI Sorting Agent, not SQL
        
        Returns:
            Dict with 'where_clause' string
        """
        prompt = f"""
You are a SQL query builder. Convert the following business rules into a PostgreSQL WHERE clause.

RULES:
{self.rules_text}

DATABASE SCHEMA:
Table: referrals
Columns:
- referral_id (TEXT)
- schedule_status (TEXT) - values: 'PENDING', 'SCHEDULED', 'COMPLETED', 'CANCELLED', 'ON_HOLD'
- auth_units_remaining (INTEGER)
- urgency (TEXT) - values: 'Urgent', 'Routine'
- contact_attempts (INTEGER)
- agent_segment (TEXT)
- patient_city (TEXT)
- service_type (TEXT)
- payer (TEXT)

IMPORTANT INSTRUCTIONS:
1. Convert all "must not be" rules to: column NOT IN ('value1', 'value2')
2. Convert all "must be" rules to: column IN ('value1', 'value2')
3. Convert all "greater than" rules to: column > value
4. Combine multiple conditions with AND
5. IGNORE any "order by" rules - sorting is handled by AI agent
6. Return ONLY valid SQL syntax, no explanations

Return in this exact format:
WHERE: <your where clause without the WHERE keyword>

Example output:
WHERE: schedule_status NOT IN ('SCHEDULED', 'COMPLETED') AND auth_units_remaining > 0
"""
        
        try:
            if self.model is None:
                raise Exception("Google Gemini not configured")
            
            response = self.model.generate_content(prompt)
            content = response.text.strip()
            
            # Parse the response
            where_clause = ""
            
            for line in content.split('\n'):
                if line.startswith('WHERE:'):
                    where_clause = line.replace('WHERE:', '').strip()
                    break
            
            print(f"✓ AI generated WHERE clause: {where_clause}")
            
            return {
                "success": True,
                "where_clause": where_clause,
                "rules_applied": self.rules_text
            }
            
        except Exception as e:
            print(f"Error generating SQL from rules: {e}")
            # Fallback to basic rules
            return {
                "success": False,
                "where_clause": "schedule_status NOT IN ('SCHEDULED', 'COMPLETED', 'CANCELLED')",
                "error": str(e)
            }
    
    def build_full_query(self, base_query: str = "SELECT * FROM referrals") -> str:
        """
        Build complete SQL query with rules applied
        
        Args:
            base_query: Base SELECT query
            
        Returns:
            Complete SQL query with WHERE and ORDER BY clauses
        """
        sql_parts = self.generate_sql_where_clause()
        
        query = base_query
        
        if sql_parts.get('where_clause'):
            query += f" WHERE {sql_parts['where_clause']}"
        
        if sql_parts.get('order_by'):
            query += f" ORDER BY {sql_parts['order_by']}"
        
        return query
    
    def reload_rules(self):
        """Reload rules from file (useful for hot-reloading)"""
        self.rules_text = self._load_rules()


# Singleton instance
rules_engine = SchedulerRulesEngine()
