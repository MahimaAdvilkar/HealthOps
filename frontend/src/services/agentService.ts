export interface WorkflowResult {
  referral_id: string;
  timestamp: string;
  agents_executed: string[];
  validation: {
    is_valid: boolean;
    issues: string[];
    warnings: string[];
    status: string;
    validation_score: number;
    priority?: string;
  };
  validation_recommendation: string;
  matches: Array<{
    caregiver_id: string;
    caregiver_name: string;
    city: string;
    skills: string;
    availability: string;
    language: string;
    match_score: number;
    match_reasons: string[];
  }>;
  matching_recommendation: string;
  schedule_recommendation: {
    referral_id: string;
    caregiver_id?: string;
    can_schedule: boolean;
    schedule_action: string;
    priority: string;
    suggested_units: number;
    rationale: string[];
    next_steps: string[];
  };
  scheduling_recommendation: string;
  final_status: string;
  final_action: string;
}

export interface PendingReferral {
  referral_id: string;
  use_case: string;
  service_type: string;
  urgency: string;
  patient_city: string;
  auth_units_remaining: number;
  referral_received_date: string;
  [key: string]: any;
}

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const agentService = {
  async processReferral(referralId: string): Promise<WorkflowResult> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/agent/process-referral?referral_id=${referralId}`,
      { method: 'POST' }
    );
    
    if (!response.ok) {
      throw new Error('Failed to process referral with agents');
    }
    
    const data = await response.json();
    return data.workflow_result;
  },

  async getPendingReferrals(): Promise<PendingReferral[]> {
    const response = await fetch(`${API_BASE_URL}/api/v1/agent/pending-referrals`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch pending referrals');
    }
    
    const data = await response.json();
    return data.referrals;
  },
};
