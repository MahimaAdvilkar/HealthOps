"""
AI Sorting Agent for Intelligent Referral Prioritization
Uses Google Gemini LLM to intelligently sort and prioritize referrals
"""

import os
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()


class SortingAgent:
    """
    Intelligent sorting agent that prioritizes referrals using Google Gemini AI
    Considers multiple factors beyond simple urgency
    """
    
    def __init__(self):
        self.model = self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize Google Gemini client"""
        google_api_key = os.getenv('GOOGLE_API_KEY')
        
        if not google_api_key or google_api_key == 'your_google_api_key_here':
            print("WARNING: GOOGLE_API_KEY not set. AI sorting will use fallback.")
            return None
        
        genai.configure(api_key=google_api_key)
        return genai.GenerativeModel('gemini-2.0-flash')
    
    def sort_referrals(self, referrals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Intelligently sort referrals using AI
        
        Args:
            referrals: List of referral dictionaries
            
        Returns:
            Sorted list of referrals (highest priority first)
        """
        if not referrals or len(referrals) <= 1:
            return referrals
        
        print(f"\n{'='*60}")
        print(f"AI SORTING AGENT - Prioritizing {len(referrals)} referrals")
        print(f"{'='*60}")
        
        # Extract key info for sorting decision
        referral_summaries = []
        for idx, ref in enumerate(referrals):
            summary = {
                "index": idx,
                "referral_id": ref.get('referral_id'),
                "urgency": ref.get('urgency', 'Routine'),
                "contact_attempts": ref.get('contact_attempts', 0),
                "auth_units_remaining": ref.get('auth_units_remaining', 0),
                "schedule_status": ref.get('schedule_status', 'PENDING'),
                "service_type": ref.get('service_type', 'Unknown'),
                "patient_age": ref.get('patient_age'),
                "payer": ref.get('payer'),
                "agent_segment": ref.get('agent_segment')
            }
            referral_summaries.append(summary)
        
        # Create sorting prompt for LLM
        prompt = f"""You are an AI agent responsible for prioritizing healthcare referrals for scheduling.

REFERRALS TO SORT (Total: {len(referral_summaries)}):
{self._format_referrals_for_llm(referral_summaries[:20])}  
{"... and " + str(len(referral_summaries) - 20) + " more" if len(referral_summaries) > 20 else ""}

PRIORITIZATION RULES (in order of importance):
1. URGENT cases always come first
2. Among urgent cases, prioritize by:
   - Fewer contact attempts (new cases need attention)
   - Lower auth units (running out of authorization)
3. ROUTINE cases come after all urgent cases
4. Among routine cases, prioritize by:
   - Fewer contact attempts
   - Service type complexity (Home Health > PT/OT > simple services)

OUTPUT FORMAT:
Return ONLY a comma-separated list of referral indices in priority order (highest to lowest).
Example: 0,3,1,2,4

Your sorted indices:"""

        try:
            if self.model is None:
                raise Exception("Google Gemini not configured")
            
            response = self.model.generate_content(prompt)
            sorted_indices_str = response.text.strip()
            
            # Parse the response
            sorted_indices = [int(idx.strip()) for idx in sorted_indices_str.split(',') if idx.strip().isdigit()]
            
            # Validate indices
            sorted_indices = [idx for idx in sorted_indices if 0 <= idx < len(referrals)]
            
            # Handle missing indices (add them at the end)
            missing_indices = [i for i in range(len(referrals)) if i not in sorted_indices]
            sorted_indices.extend(missing_indices)
            
            # Apply sorting
            sorted_referrals = [referrals[idx] for idx in sorted_indices]
            
            print(f"✓ Sorted {len(sorted_referrals)} referrals by AI priority")
            print(f"Top 3 priorities:")
            for i, ref in enumerate(sorted_referrals[:3], 1):
                print(f"  {i}. {ref.get('referral_id')} - {ref.get('urgency')} - {ref.get('contact_attempts', 0)} attempts")
            print(f"{'='*60}\n")
            
            return sorted_referrals
            
        except Exception as e:
            print(f"AI Sorting failed: {e}")
            print(f"Falling back to basic urgency sorting")
            # Fallback: simple urgency-based sorting
            return sorted(
                referrals,
                key=lambda x: (
                    0 if x.get('urgency') == 'Urgent' else 1,
                    x.get('contact_attempts', 0)
                )
            )
    
    def _format_referrals_for_llm(self, summaries: List[Dict]) -> str:
        """Format referral summaries for LLM prompt"""
        lines = []
        for summary in summaries:
            lines.append(
                f"[{summary['index']}] {summary['referral_id']} | "
                f"Urgency: {summary['urgency']} | "
                f"Attempts: {summary['contact_attempts']} | "
                f"Auth Units: {summary['auth_units_remaining']} | "
                f"Service: {summary['service_type']}"
            )
        return '\n'.join(lines)


# Singleton instance
sorting_agent = SortingAgent()
