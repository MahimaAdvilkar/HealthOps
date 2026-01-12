import os
import yaml
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

# Try to import Google Generative AI
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google-generativeai not installed. Using fallback logic.")


class ConfigLoader:
    """Loads configuration from .env and YAML files"""
    
    def __init__(self, env_path: str = None):
        if env_path is None:
            current_dir = Path(__file__).parent.parent.parent
            env_path = current_dir / ".env"
        self.env_path = env_path
        self._load_env()
        self._load_yaml_config()
    
    def _load_env(self):
        load_dotenv(self.env_path)
    
    def _load_yaml_config(self):
        """Load YAML configuration file"""
        config_path = os.getenv("AGENT_CONFIG_PATH", "config/agent_config.yaml")
        current_dir = Path(__file__).parent.parent.parent
        full_path = current_dir / config_path
        
        try:
            with open(full_path, 'r') as f:
                self.yaml_config = yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Warning: Config file not found at {full_path}, using defaults")
            self.yaml_config = {}
    
    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """Get value from environment variables"""
        return os.getenv(key, default)
    
    def get_yaml(self, *keys, default: Any = None) -> Any:
        """Get value from YAML config using dot notation"""
        value = self.yaml_config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            if value is None:
                return default
        return value


class ReferralValidationAgent:
    """
    Agent 1: Validates referral/client information
    Checks: insurance status, authorization, urgency, completeness
    All scoring thresholds loaded from YAML config
    Uses Google Gemini for AI recommendations
    """
    
    def __init__(self):
        self.config = ConfigLoader()
        self.agent_name = "Referral Validation Agent"
        self.google_api_key = self.config.get("GOOGLE_API_KEY")
        self.gemini_model = None
        
        # Initialize Gemini
        if GEMINI_AVAILABLE and self.google_api_key:
            try:
                genai.configure(api_key=self.google_api_key)
                self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')
                print(f"[{self.agent_name}] Gemini AI initialized")
            except Exception as e:
                print(f"[{self.agent_name}] Gemini init failed: {e}")
        
        # Load all scoring parameters from config
        self.insurance_penalty = self.config.get_yaml('validation_agent', 'scoring', 'insurance_inactive_penalty', default=30)
        self.auth_penalty = self.config.get_yaml('validation_agent', 'scoring', 'auth_not_approved_penalty', default=40)
        self.no_units_penalty = self.config.get_yaml('validation_agent', 'scoring', 'no_auth_units_penalty', default=35)
        self.docs_penalty = self.config.get_yaml('validation_agent', 'scoring', 'docs_incomplete_penalty', default=10)
        self.assessment_penalty = self.config.get_yaml('validation_agent', 'scoring', 'no_home_assessment_penalty', default=10)
        self.responsiveness_penalty = self.config.get_yaml('validation_agent', 'scoring', 'low_responsiveness_penalty', default=5)
        
        self.high_contact_threshold = self.config.get_yaml('validation_agent', 'thresholds', 'high_contact_attempts', default=5)
        self.passing_score = self.config.get_yaml('validation_agent', 'thresholds', 'passing_score', default=70)
        
        self.status_ready = self.config.get_yaml('validation_agent', 'status_mapping', 'ready', default='READY')
        self.status_warnings = self.config.get_yaml('validation_agent', 'status_mapping', 'ready_with_warnings', default='READY_WITH_WARNINGS')
        self.status_blocked = self.config.get_yaml('validation_agent', 'status_mapping', 'blocked', default='BLOCKED')
        self.status_needs_docs = self.config.get_yaml('validation_agent', 'status_mapping', 'needs_docs', default='NEEDS_DOCS')
    
    def validate_referral(self, referral: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate if referral is good for scheduling
        """
        validation_results = {
            "referral_id": referral.get("referral_id"),
            "is_valid": True,
            "issues": [],
            "warnings": [],
            "status": self.status_ready,
            "validation_score": 100
        }
        
        # Check insurance active
        if referral.get("insurance_active") != "Y":
            validation_results["issues"].append("Insurance is not active")
            validation_results["is_valid"] = False
            validation_results["status"] = self.status_blocked
            validation_results["validation_score"] -= self.insurance_penalty
        
        # Check authorization
        if referral.get("auth_required") == "Y":
            if referral.get("auth_status") != "APPROVED":
                validation_results["issues"].append("Authorization not approved")
                validation_results["is_valid"] = False
                validation_results["status"] = self.status_blocked
                validation_results["validation_score"] -= self.auth_penalty
            
            # Check auth units remaining
            if referral.get("auth_units_remaining", 0) <= 0:
                validation_results["issues"].append("No authorization units remaining")
                validation_results["is_valid"] = False
                validation_results["status"] = self.status_blocked
                validation_results["validation_score"] -= self.no_units_penalty
        
        # Check if docs are complete
        if referral.get("docs_complete") != "Y":
            validation_results["warnings"].append("Documentation incomplete")
            validation_results["validation_score"] -= self.docs_penalty
            if validation_results["status"] == self.status_ready:
                validation_results["status"] = self.status_needs_docs
        
        # Check home assessment
        if referral.get("home_assessment_done") != "Y":
            validation_results["warnings"].append("Home assessment not completed")
            validation_results["validation_score"] -= self.assessment_penalty
        
        # Check patient responsiveness
        patient_responsive = referral.get("patient_responsive", "LOW")
        if patient_responsive == "LOW":
            validation_results["warnings"].append("Low patient responsiveness")
            validation_results["validation_score"] -= self.responsiveness_penalty
        
        # Check urgency
        if referral.get("urgency") == "Urgent":
            validation_results["priority"] = "HIGH"
        else:
            validation_results["priority"] = "NORMAL"
        
        # Check contact attempts
        contact_attempts = referral.get("contact_attempts", 0)
        if contact_attempts > self.high_contact_threshold:
            validation_results["warnings"].append(f"High contact attempts: {contact_attempts}")
        
        # Final status determination
        if validation_results["is_valid"]:
            if len(validation_results["warnings"]) == 0:
                validation_results["status"] = self.status_ready
            else:
                validation_results["status"] = self.status_warnings
        
        return validation_results
    
    def get_agent_recommendation(self, validation: Dict[str, Any]) -> str:
        """
        Get AI agent recommendation based on validation using Google Gemini
        """
        prompt = f"""You are a healthcare referral validation agent. Based on this validation result, provide a brief actionable recommendation (1-2 sentences).

Referral ID: {validation.get('referral_id')}
Status: {validation['status']}
Validation Score: {validation['validation_score']}/100
Issues: {', '.join(validation['issues']) if validation['issues'] else 'None'}
Warnings: {', '.join(validation['warnings']) if validation['warnings'] else 'None'}
Priority: {validation.get('priority', 'NORMAL')}

Respond with a clear action: PROCEED, HOLD, or BLOCK, followed by specific next steps."""

        # Try Gemini AI
        if self.gemini_model:
            try:
                response = self.gemini_model.generate_content(prompt)
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                print(f"[{self.agent_name}] Gemini failed: {e}")
        
        # Fallback to rule-based
        if validation["status"] == "BLOCKED":
            return f"HOLD: Cannot proceed. Issues: {', '.join(validation['issues'])}"
        elif validation["status"] == "READY":
            return f"PROCEED: Referral validated. Priority: {validation['priority']}"
        elif validation["status"] == "READY_WITH_WARNINGS":
            return f"PROCEED WITH CAUTION: {', '.join(validation['warnings'])}"
        else:
            return f"REVIEW: {validation['status']}"


class CaregiverMatchingAgent:
    """
    Agent 2: Matches caregivers to referrals based on location, skills, availability
    All scoring weights and thresholds loaded from YAML config
    Uses Google Gemini for AI recommendations
    """
    
    def __init__(self):
        self.config = ConfigLoader()
        self.agent_name = "Caregiver Matching Agent"
        self.google_api_key = self.config.get("GOOGLE_API_KEY")
        self.gemini_model = None
        
        # Initialize Gemini
        if GEMINI_AVAILABLE and self.google_api_key:
            try:
                genai.configure(api_key=self.google_api_key)
                self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')
                print(f"[{self.agent_name}] Gemini AI initialized")
            except Exception as e:
                print(f"[{self.agent_name}] Gemini init failed: {e}")
        
        # Load scoring parameters from config
        self.city_match_points = self.config.get_yaml('matching_agent', 'scoring', 'city_match_points', default=40)
        self.exact_skill_points = self.config.get_yaml('matching_agent', 'scoring', 'exact_skill_match_points', default=40)
        self.general_skill_points = self.config.get_yaml('matching_agent', 'scoring', 'general_skill_match_points', default=20)
        self.flexible_availability_points = self.config.get_yaml('matching_agent', 'scoring', 'flexible_availability_points', default=20)
        self.partial_availability_points = self.config.get_yaml('matching_agent', 'scoring', 'partial_availability_points', default=10)
        
        self.min_match_score = self.config.get_yaml('matching_agent', 'thresholds', 'minimum_match_score', default=30)
        self.max_matches = self.config.get_yaml('matching_agent', 'thresholds', 'max_matches_returned', default=5)
        
        self.general_skills = self.config.get_yaml('matching_agent', 'general_skills', default=["ECM", "HOME", "CARE"])
    
    def match_caregivers(
        self, 
        referral: Dict[str, Any], 
        caregivers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Find matching caregivers for a referral
        """
        matches = []
        
        referral_city = referral.get("patient_city", "").strip()
        referral_service = referral.get("use_case", "").strip()
        
        for caregiver in caregivers:
            # Only active caregivers
            if caregiver.get("active") != "Y":
                continue
            
            match_score = 0
            match_details = {
                "caregiver_id": caregiver.get("caregiver_id"),
                "caregiver_name": f"Caregiver {caregiver.get('caregiver_id')}",
                "city": caregiver.get("city"),
                "skills": caregiver.get("skills"),
                "availability": caregiver.get("availability"),
                "language": caregiver.get("primary_language"),
                "match_score": 0,
                "match_reasons": []
            }
            
            # City match (configurable points)
            if caregiver.get("city", "").strip() == referral_city:
                match_score += self.city_match_points
                match_details["match_reasons"].append(f"Same city: {referral_city}")
            
            # Skills match (configurable points)
            caregiver_skills = caregiver.get("skills", "").upper()
            if referral_service.upper() in caregiver_skills:
                match_score += self.exact_skill_points
                match_details["match_reasons"].append(f"Has skill: {referral_service}")
            elif any(skill in caregiver_skills for skill in self.general_skills):
                match_score += self.general_skill_points
                match_details["match_reasons"].append("Has general home care skills")
            
            # Availability (configurable points)
            availability = caregiver.get("availability", "")
            if "Flexible" in availability or "Full-Time" in availability:
                match_score += self.flexible_availability_points
                match_details["match_reasons"].append(f"Good availability: {availability}")
            elif availability:
                match_score += self.partial_availability_points
            
            match_details["match_score"] = match_score
            
            # Only include matches with score > configured minimum
            if match_score >= self.min_match_score:
                matches.append(match_details)
        
        # Sort by match score (highest first)
        matches.sort(key=lambda x: x["match_score"], reverse=True)
        
        return matches[:self.max_matches]  # Return top N matches from config
    
    def get_agent_recommendation(
        self, 
        referral_id: str, 
        matches: List[Dict[str, Any]]
    ) -> str:
        """
        Get AI agent recommendation for caregiver matching using Google Gemini
        """
        if not matches:
            return f"NO MATCHES: No caregivers found in the area for {referral_id}"
        
        # Use Gemini AI to generate recommendation
        if self.gemini_model:
            try:
                match_summary = f"{len(matches)} caregivers found\n"
                for i, m in enumerate(matches[:3], 1):
                    match_summary += f"{i}. {m['caregiver_id']}: {m['match_score']}% - {', '.join(m['match_reasons'][:2])}\n"
                
                prompt = f"""As a healthcare caregiver matching expert, provide a brief recommendation (1-2 sentences) for this referral:

Referral: {referral_id}
{match_summary}

Recommend which caregiver to assign and why. Be specific about the best match."""

                response = self.gemini_model.generate_content(prompt)
                recommendation = response.text.strip()
                print(f"[{self.agent_name}] Gemini recommendation: {recommendation[:100]}...")
                return recommendation
                
            except Exception as e:
                print(f"[{self.agent_name}] Gemini recommendation failed: {e}")
        
        # Fallback to rule-based only if Gemini unavailable
        print(f"[{self.agent_name}] Using fallback rule-based recommendation")
        if len(matches) >= 3:
            return f"EXCELLENT: Found {len(matches)} matching caregivers. Top match: {matches[0]['caregiver_id']} ({matches[0]['match_score']}%)"
        elif len(matches) > 0:
            return f"GOOD: Found {len(matches)} caregiver(s). Assign {matches[0]['caregiver_id']} (score: {matches[0]['match_score']}%)"
        return f"LIMITED: Only {len(matches)} match found"


class SchedulingAgent:
    """
    Agent 3: Creates scheduling recommendations
    All limits and thresholds loaded from YAML config
    Uses Google Gemini for AI recommendations
    """
    
    def __init__(self):
        self.config = ConfigLoader()
        self.agent_name = "Scheduling Agent"
        self.google_api_key = self.config.get("GOOGLE_API_KEY")
        self.gemini_model = None
        
        # Initialize Gemini
        if GEMINI_AVAILABLE and self.google_api_key:
            try:
                genai.configure(api_key=self.google_api_key)
                self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')
                print(f"[{self.agent_name}] Gemini AI initialized")
            except Exception as e:
                print(f"[{self.agent_name}] Gemini init failed: {e}")
        
        # Load scheduling parameters from config
        self.max_units_per_week = self.config.get_yaml('scheduling_agent', 'limits', 'max_units_per_week', default=20)
        self.max_pending_referrals = self.config.get_yaml('scheduling_agent', 'limits', 'max_pending_referrals', default=50)
        
        self.urgent_keywords = self.config.get_yaml('scheduling_agent', 'priorities', 'urgent_keywords', default=["Urgent"])
        self.high_priority = self.config.get_yaml('scheduling_agent', 'priorities', 'high_priority', default="HIGH")
        self.normal_priority = self.config.get_yaml('scheduling_agent', 'priorities', 'normal_priority', default="NORMAL")
        
        self.action_schedule = self.config.get_yaml('scheduling_agent', 'actions', 'schedule_now', default="SCHEDULE_NOW")
        self.action_hold = self.config.get_yaml('scheduling_agent', 'actions', 'hold', default="HOLD")
        self.action_block = self.config.get_yaml('scheduling_agent', 'actions', 'block', default="BLOCK")
        
        self.min_suggested_units = self.config.get_yaml('scheduling_agent', 'unit_calculation', 'min_suggested_units', default=1)
        self.default_buffer = self.config.get_yaml('scheduling_agent', 'unit_calculation', 'default_buffer', default=0)
    
    def create_schedule_recommendation(
        self,
        referral: Dict[str, Any],
        validation: Dict[str, Any],
        caregiver_match: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create scheduling recommendation based on referral, validation, and caregiver match
        """
        recommendation = {
            "referral_id": referral.get("referral_id"),
            "caregiver_id": caregiver_match.get("caregiver_id") if caregiver_match else None,
            "can_schedule": False,
            "schedule_action": self.action_hold,
            "priority": self.normal_priority,
            "suggested_units": 0,
            "rationale": [],
            "next_steps": []
        }
        
        # Determine priority FIRST using configured urgent keywords (always check this)
        urgency = referral.get("urgency", "")
        if any(keyword in urgency for keyword in self.urgent_keywords):
            recommendation["priority"] = self.high_priority
        
        if validation.get("priority") == self.high_priority:
            recommendation["priority"] = self.high_priority
        
        # Check if we can schedule
        if not validation.get("is_valid"):
            recommendation["schedule_action"] = self.action_block
            recommendation["rationale"].append("Referral validation failed")
            recommendation["next_steps"].append("Resolve validation issues first")
            return recommendation
        
        # Check prerequisites: docs and home assessment must be complete before scheduling
        docs_complete = referral.get("docs_complete", "N") == "Y"
        home_assessment_done = referral.get("home_assessment_done", "N") == "Y"
        
        if not docs_complete:
            recommendation["schedule_action"] = self.action_hold
            recommendation["rationale"].append("Documentation incomplete - cannot schedule")
            recommendation["next_steps"].append("Complete required documentation first")
            if not home_assessment_done:
                recommendation["rationale"].append("Home assessment not completed")
                recommendation["next_steps"].append("Schedule and complete home assessment")
            return recommendation
        
        if not home_assessment_done:
            recommendation["schedule_action"] = self.action_hold
            recommendation["rationale"].append("Home assessment not completed - cannot schedule")
            recommendation["next_steps"].append("Schedule and complete home assessment first")
            return recommendation
        
        if not caregiver_match:
            recommendation["schedule_action"] = self.action_hold
            recommendation["rationale"].append("No caregiver matched")
            recommendation["next_steps"].append("Find suitable caregiver")
            return recommendation
        
        # All prerequisites met - can schedule!
        recommendation["can_schedule"] = True
        recommendation["schedule_action"] = self.action_schedule
        
        # Add urgency to rationale if high priority
        if recommendation["priority"] == self.high_priority:
            recommendation["rationale"].append(f"{urgency} referral - high priority")
        
        # Calculate units to schedule using configured max
        units_remaining = referral.get("auth_units_remaining", 0)
        units_scheduled = referral.get("units_scheduled_next_7d", 0)
        
        # Suggest scheduling units for next 7 days
        if units_remaining > 0:
            suggested = min(units_remaining - units_scheduled, self.max_units_per_week)
            recommendation["suggested_units"] = max(suggested, self.default_buffer)
            recommendation["rationale"].append(f"Suggest {recommendation['suggested_units']} units for next 7 days")
        
        # Check patient waiting status
        schedule_status = referral.get("schedule_status")
        if schedule_status == "NOT_SCHEDULED":
            recommendation["rationale"].append("Patient waiting - needs immediate scheduling")
            recommendation["next_steps"].append("Contact patient to confirm availability")
        
        # Add next steps
        recommendation["next_steps"].extend([
            f"Assign caregiver: {caregiver_match.get('caregiver_id')}",
            f"Schedule {recommendation['suggested_units']} {referral.get('unit_type', 'units')}",
            "Send confirmation to patient and caregiver",
            "Update referral status to SCHEDULED"
        ])
        
        return recommendation
    
    def get_agent_recommendation(self, schedule_rec: Dict[str, Any]) -> str:
        """
        Get AI agent recommendation for scheduling using Google Gemini
        """
        action = schedule_rec.get("schedule_action")
        priority = schedule_rec.get("priority")
        rationale = ', '.join(schedule_rec['rationale'])
        
        # Use Gemini AI to generate recommendation
        if self.gemini_model:
            try:
                prompt = f"""As a healthcare scheduling coordinator, provide a brief action recommendation (1-2 sentences) for this scheduling decision:

Action: {action}
Priority: {priority}
Can Schedule: {schedule_rec.get('can_schedule')}
Caregiver: {schedule_rec.get('caregiver_id', 'None')}
Suggested Units: {schedule_rec.get('suggested_units')}
Rationale: {rationale}

Provide clear next steps for the coordinator."""

                response = self.gemini_model.generate_content(prompt)
                recommendation = response.text.strip()
                print(f"[{self.agent_name}] Gemini recommendation: {recommendation[:100]}...")
                return recommendation
                
            except Exception as e:
                print(f"[{self.agent_name}] Gemini recommendation failed: {e}")
        
        # Fallback to rule-based only if Gemini unavailable
        print(f"[{self.agent_name}] Using fallback rule-based recommendation")
        if action == "SCHEDULE_NOW":
            return f"SCHEDULE NOW [{priority}]: {rationale}"
        elif action == "HOLD":
            return f"HOLD: {rationale}"
        else:
            return f"BLOCK: Cannot schedule. {rationale}"


class AgentWorkflow:
    """
    Orchestrates the 3-agent workflow
    """
    
    def __init__(self):
        self.validation_agent = ReferralValidationAgent()
        self.matching_agent = CaregiverMatchingAgent()
        self.scheduling_agent = SchedulingAgent()
    
    def process_referral(
        self,
        referral: Dict[str, Any],
        caregivers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Run complete workflow: validate -> match -> schedule
        """
        workflow_result = {
            "referral_id": referral.get("referral_id"),
            "timestamp": datetime.now().isoformat(),
            "agents_executed": []
        }
        
        # Agent 1: Validate
        print(f"\nAgent 1: Validating referral {referral.get('referral_id')}...")
        validation = self.validation_agent.validate_referral(referral)
        validation_rec = self.validation_agent.get_agent_recommendation(validation)
        
        workflow_result["validation"] = validation
        workflow_result["validation_recommendation"] = validation_rec
        workflow_result["agents_executed"].append("ReferralValidationAgent")
        
        # Check prerequisites before caregiver matching
        docs_complete = referral.get("docs_complete", "N") == "Y"
        home_assessment_done = referral.get("home_assessment_done", "N") == "Y"
        
        # Agent 2: Match caregivers (only if validation passed AND docs complete AND home assessment done)
        matches = []
        if not validation.get("is_valid"):
            workflow_result["matches"] = []
            workflow_result["matching_recommendation"] = "SKIPPED: Validation failed"
        elif not docs_complete:
            workflow_result["matches"] = []
            workflow_result["matching_recommendation"] = "SKIPPED: Documentation incomplete - complete docs first"
        elif not home_assessment_done:
            workflow_result["matches"] = []
            workflow_result["matching_recommendation"] = "SKIPPED: Home assessment pending - complete assessment first"
        else:
            print(f"Agent 2: Finding matching caregivers...")
            matches = self.matching_agent.match_caregivers(referral, caregivers)
            matching_rec = self.matching_agent.get_agent_recommendation(
                referral.get("referral_id"), 
                matches
            )
            
            workflow_result["matches"] = matches
            workflow_result["matching_recommendation"] = matching_rec
            workflow_result["agents_executed"].append("CaregiverMatchingAgent")
        
        # Agent 3: Create schedule recommendation
        print(f"Agent 3: Creating schedule recommendation...")
        top_match = matches[0] if matches else None
        schedule_rec = self.scheduling_agent.create_schedule_recommendation(
            referral, 
            validation, 
            top_match
        )
        scheduling_recommendation = self.scheduling_agent.get_agent_recommendation(schedule_rec)
        
        workflow_result["schedule_recommendation"] = schedule_rec
        workflow_result["scheduling_recommendation"] = scheduling_recommendation
        workflow_result["agents_executed"].append("SchedulingAgent")
        
        # Final workflow status - based on schedule recommendation
        if schedule_rec.get("can_schedule"):
            workflow_result["final_status"] = "READY_TO_SCHEDULE"
            workflow_result["final_action"] = "Proceed with scheduling"
        elif not validation.get("is_valid"):
            workflow_result["final_status"] = "BLOCKED"
            workflow_result["final_action"] = "Resolve validation issues: " + ", ".join(validation.get("issues", []))
        else:
            # Validation passed but can't schedule - check why
            action = schedule_rec.get("schedule_action", "HOLD")
            rationale = schedule_rec.get("rationale", [])
            next_steps = schedule_rec.get("next_steps", [])
            
            # Determine specific status based on reason
            if any("Documentation" in r for r in rationale):
                workflow_result["final_status"] = "PENDING_DOCUMENTATION"
                workflow_result["final_action"] = "Complete required documentation"
            elif any("Home assessment" in r or "assessment" in r for r in rationale):
                workflow_result["final_status"] = "PENDING_HOME_ASSESSMENT"
                workflow_result["final_action"] = "Schedule and complete home assessment"
            elif not top_match:
                workflow_result["final_status"] = "PENDING_CAREGIVER"
                workflow_result["final_action"] = "Find suitable caregiver in area"
            else:
                workflow_result["final_status"] = "ON_HOLD"
                workflow_result["final_action"] = next_steps[0] if next_steps else "Review and resolve blockers"
        
        return workflow_result
