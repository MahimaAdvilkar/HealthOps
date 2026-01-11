"""
Crew AI Workflow for HealthOps Referral Processing
Uses Crew AI framework to orchestrate healthcare referral agents
"""

import os
from typing import Dict, Any, List
from pathlib import Path
from crewai import Agent, Task, Crew, Process, LLM
from dotenv import load_dotenv
import yaml
from datetime import datetime
import json

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)


class HealthOpsCrewWorkflow:
    """
    Crew AI orchestration for healthcare referral processing
    Manages: Referral validation, caregiver matching, compliance checking
    Uses Swarms API for LLM calls
    """
    
    def __init__(self):
        self.config = self._load_config()
        self.llm = self._get_swarms_llm()
        self.execution_history = []  # Track agent execution history
        self.max_history = self.config.get('crew_ai', {}).get('monitoring', {}).get('max_history_size', 100)
        
        # Load scoring configuration
        crew_config = self.config.get('crew_ai', {})
        self.city_match_points = crew_config.get('scoring', {}).get('city_match_points', 40)
        self.exact_skill_match_points = crew_config.get('scoring', {}).get('exact_skill_match_points', 40)
        self.general_skill_match_points = crew_config.get('scoring', {}).get('general_skill_match_points', 20)
        self.flexible_availability_points = crew_config.get('scoring', {}).get('flexible_availability_points', 20)
        self.partial_availability_points = crew_config.get('scoring', {}).get('partial_availability_points', 10)
        self.max_matches_returned = crew_config.get('thresholds', {}).get('max_matches_returned', 3)
        
    def _load_config(self) -> Dict[str, Any]:
        """Load agent configuration from YAML"""
        config_path = Path(__file__).parent.parent.parent / "config" / "agent_config.yaml"
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Warning: Config file not found at {config_path}")
            return {}
    
    def _get_swarms_llm(self) -> LLM:
        """Configure Crew AI to use Swarms API (OpenAI-compatible endpoint)"""
        swarms_api_key = os.getenv("SWARMS_API_KEY")
        
        if not swarms_api_key:
            raise ValueError("SWARMS_API_KEY not found in environment variables")
        
        # Load LLM config from agent_config.yaml
        llm_config = self.config.get('crew_ai', {}).get('llm', {})
        model = llm_config.get('model', 'gpt-4o')
        temperature = llm_config.get('temperature', 0.7)
        base_url = llm_config.get('base_url', 'https://api.swarms.world/v1')
        
        # Crew AI supports OpenAI-compatible endpoints
        # Swarms API is OpenAI-compatible, so we can use it directly
        return LLM(
            model=model,
            api_key=swarms_api_key,
            base_url=base_url,
            temperature=temperature
        )
    
    def create_referral_validation_agent(self) -> Agent:
        """
        Agent 1: Referral Validation Specialist
        Validates insurance, authorization, documentation completeness
        """
        return Agent(
            role="Referral Validation Specialist",
            goal="Validate referrals for completeness, insurance eligibility, and authorization status",
            backstory="""You are an expert healthcare referral coordinator with 10+ years experience.
            You meticulously verify insurance coverage, authorization approvals, and documentation 
            completeness before any patient scheduling. You follow strict compliance protocols and 
            never approve incomplete or unauthorized referrals.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    def create_caregiver_matching_agent(self) -> Agent:
        """
        Agent 2: Caregiver Matching Specialist
        Matches validated referrals with qualified caregivers based on skills, location, availability
        """
        return Agent(
            role="Caregiver Matching Specialist",
            goal="Match validated referrals with the most qualified and available caregivers",
            backstory="""You are a skilled care coordination manager who excels at matching patients 
            with the perfect caregivers. You consider geographic proximity, skill sets, availability, 
            and patient needs. You prioritize urgent cases and ensure optimal caregiver utilization.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    def create_compliance_agent(self) -> Agent:
        """
        Agent 3: Compliance & Documentation Specialist
        Ensures all documentation meets regulatory requirements
        """
        return Agent(
            role="Compliance & Documentation Specialist",
            goal="Ensure all referral documentation meets healthcare regulatory and compliance standards",
            backstory="""You are a healthcare compliance expert with deep knowledge of HIPAA, 
            state regulations, and insurance requirements. You review all documentation for 
            completeness, accuracy, and regulatory compliance before final approval.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    def create_validation_task(self, agent: Agent, referral_data: Dict[str, Any]) -> Task:
        """Create validation task for a referral"""
        return Task(
            description=f"""
            Validate the following referral for processing:
            
            Referral ID: {referral_data.get('referral_id')}
            Insurance Active: {referral_data.get('insurance_active')}
            Authorization Status: {referral_data.get('auth_status')}
            Authorization Units: {referral_data.get('auth_units_remaining')}
            Documentation Complete: {referral_data.get('docs_complete')}
            Urgency: {referral_data.get('urgency')}
            
            Check:
            1. Insurance is active
            2. Authorization is approved (if required)
            3. Authorization units are available
            4. Documentation is complete
            5. Assign priority level
            
            Return validation status: READY, BLOCKED, or NEEDS_DOCS
            Include validation score (0-100) and list of any issues.
            """,
            agent=agent,
            expected_output="Validation status with score, issues list, and priority level"
        )
    
    def create_matching_task(self, agent: Agent, referral_data: Dict[str, Any], 
                            caregivers: List[Dict[str, Any]]) -> Task:
        """Create caregiver matching task"""
        caregiver_list = "\n".join([
            f"- {cg.get('caregiver_name')} | Skills: {cg.get('skills')} | "
            f"City: {cg.get('city')} | Available: {cg.get('availability')}"
            for cg in caregivers[:10]  # Limit to top 10 for LLM context
        ])
        
        return Task(
            description=f"""
            Match this validated referral with the best caregiver:
            
            Referral ID: {referral_data.get('referral_id')}
            Patient City: {referral_data.get('city')}
            Required Services: {referral_data.get('service_type')}
            Urgency: {referral_data.get('urgency')}
            
            Available Caregivers:
            {caregiver_list}
            
            Score each caregiver based on:
            1. Geographic proximity (same city = +{self.city_match_points} points)
            2. Skill match (exact = +{self.exact_skill_match_points}, general = +{self.general_skill_match_points})
            3. Availability (flexible = +{self.flexible_availability_points}, partial = +{self.partial_availability_points})
            
            Return top {self.max_matches_returned} matches with scores and reasoning.
            """,
            agent=agent,
            expected_output="Top 3 caregiver matches with match scores and justification"
        )
    
    def create_compliance_task(self, agent: Agent, referral_data: Dict[str, Any]) -> Task:
        """Create compliance verification task"""
        return Task(
            description=f"""
            Perform final compliance review for:
            
            Referral ID: {referral_data.get('referral_id')}
            Validation Status: {referral_data.get('validation_status')}
            Assigned Caregiver: {referral_data.get('assigned_caregiver', 'TBD')}
            
            Verify:
            1. All required HIPAA documentation is present
            2. Insurance authorization is properly documented
            3. Patient consent forms are complete
            4. Service agreements are in place
            5. No regulatory red flags
            
            Return: APPROVED or NEEDS_REVIEW with detailed compliance checklist.
            """,
            agent=agent,
            expected_output="Compliance status (APPROVED/NEEDS_REVIEW) with detailed checklist"
        )
    
    def process_referral(self, referral_data: Dict[str, Any], 
                        caregivers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Main workflow: Process a referral through all agents
        
        Args:
            referral_data: Referral information dictionary
            caregivers: List of available caregivers
            
        Returns:
            Complete processing result with validation, matching, and compliance status
        """
        referral_id = referral_data.get("referral_id", "UNKNOWN")
        start_time = datetime.now()
        
        # Log execution start
        execution_log = {
            "referral_id": referral_id,
            "start_time": start_time.isoformat(),
            "status": "RUNNING",
            "agents_executed": [],
            "tasks_completed": []
        }
        
        print(f"\n{'='*60}")
        print(f"CREW AI WORKFLOW STARTED - Referral: {referral_id}")
        print(f"{'='*60}\n")
        
        # Create agents
        print("Creating AI Agents...")
        validation_agent = self.create_referral_validation_agent()
        matching_agent = self.create_caregiver_matching_agent()
        compliance_agent = self.create_compliance_agent()
        execution_log["agents_executed"] = ["Validation", "Matching", "Compliance"]
        
        # Create tasks
        print("Creating Tasks...")
        validation_task = self.create_validation_task(validation_agent, referral_data)
        matching_task = self.create_matching_task(matching_agent, referral_data, caregivers)
        compliance_task = self.create_compliance_task(compliance_agent, referral_data)
        
        # Create crew with sequential process
        print("Initializing Crew...\n")
        crew = Crew(
            agents=[validation_agent, matching_agent, compliance_agent],
            tasks=[validation_task, matching_task, compliance_task],
            process=Process.sequential,  # Tasks run in order
            verbose=True
        )
        
        # Execute the crew
        try:
            print(f"Executing Crew Workflow for {referral_id}...\n")
            result = crew.kickoff()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            execution_log.update({
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "status": "COMPLETED",
                "tasks_completed": ["Validation", "Matching", "Compliance"],
                "result": str(result)[:500]  # Store first 500 chars
            })
            
            # Add to history
            self._add_to_history(execution_log)
            
            print(f"\n{'='*60}")
            print(f"WORKFLOW COMPLETED - Duration: {duration:.2f}s")
            print(f"{'='*60}\n")
            
            return {
                "success": True,
                "referral_id": referral_id,
                "crew_result": str(result),
                "workflow_status": "COMPLETED",
                "duration_seconds": duration,
                "message": "Referral processed through Crew AI workflow"
            }
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            execution_log.update({
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "status": "FAILED",
                "error": str(e)
            })
            
            # Add to history
            self._add_to_history(execution_log)
            
            print(f"\n{'='*60}")
            print(f"WORKFLOW FAILED - Duration: {duration:.2f}s")
            print(f"Error: {str(e)}")
            print(f"{'='*60}\n")
            
            return {
                "success": False,
                "referral_id": referral_id,
                "error": str(e),
                "workflow_status": "FAILED",
                "duration_seconds": duration
            }
    
    def _add_to_history(self, execution_log: Dict[str, Any]):
        """Add execution to history, maintain max size"""
        self.execution_history.append(execution_log)
        if len(self.execution_history) > self.max_history:
            self.execution_history.pop(0)  # Remove oldest
    
    def get_execution_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent execution history"""
        return self.execution_history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get workflow statistics"""
        if not self.execution_history:
            return {
                "total_executions": 0,
                "successful": 0,
                "failed": 0,
                "average_duration": 0
            }
        
        successful = len([e for e in self.execution_history if e.get("status") == "COMPLETED"])
        failed = len([e for e in self.execution_history if e.get("status") == "FAILED"])
        durations = [e.get("duration_seconds", 0) for e in self.execution_history if "duration_seconds" in e]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            "total_executions": len(self.execution_history),
            "successful": successful,
            "failed": failed,
            "success_rate": f"{(successful/len(self.execution_history)*100):.1f}%" if self.execution_history else "0%",
            "average_duration": f"{avg_duration:.2f}s"
        }
    
    def process_batch_referrals(self, referrals: List[Dict[str, Any]], 
                                caregivers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process multiple referrals in batch
        
        Args:
            referrals: List of referral dictionaries
            caregivers: List of available caregivers
            
        Returns:
            List of processing results
        """
        results = []
        for referral in referrals:
            result = self.process_referral(referral, caregivers)
            results.append(result)
        
        return results

