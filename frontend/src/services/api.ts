const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface Referral {
  referral_id: string;
  use_case?: string;
  service_type?: string;
  urgency?: string;
  patient_city?: string;
  agent_segment?: string;
  agent_next_action?: string;
  schedule_status?: string;
  auth_units_remaining?: number;
  contact_attempts?: number;
  payer?: string;
  patient_age?: number;
  patient_gender?: string;
  referral_received_date?: string;
  [key: string]: any;
}

export interface Caregiver {
  caregiver_id: string;
  gender?: string;
  age?: number;
  primary_language?: string;
  skills?: string;
  employment_type?: string;
  availability?: string;
  city?: string;
  active?: string;
  [key: string]: any;
}

export interface Stats {
  total_referrals: number;
  active_referrals: number;
  total_caregivers: number;
  active_caregivers: number;
}

export const apiService = {
  async getReferrals(params?: {
    limit?: number;
    offset?: number;
    urgency?: string;
    agent_segment?: string;
    schedule_status?: string;
  }): Promise<Referral[]> {
    const queryParams = new URLSearchParams();
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.offset) queryParams.append('offset', params.offset.toString());
    if (params?.urgency) queryParams.append('urgency', params.urgency);
    if (params?.agent_segment) queryParams.append('agent_segment', params.agent_segment);
    if (params?.schedule_status) queryParams.append('schedule_status', params.schedule_status);

    const response = await fetch(`${API_BASE_URL}/api/v1/referrals?${queryParams}`);
    if (!response.ok) {
      throw new Error('Failed to fetch referrals');
    }
    return response.json();
  },

  async getCaregivers(params?: {
    limit?: number;
    offset?: number;
    city?: string;
    active?: string;
    skills?: string;
  }): Promise<Caregiver[]> {
    const queryParams = new URLSearchParams();
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.offset) queryParams.append('offset', params.offset.toString());
    if (params?.city) queryParams.append('city', params.city);
    if (params?.active) queryParams.append('active', params.active);
    if (params?.skills) queryParams.append('skills', params.skills);

    const response = await fetch(`${API_BASE_URL}/api/v1/caregivers?${queryParams}`);
    if (!response.ok) {
      throw new Error('Failed to fetch caregivers');
    }
    return response.json();
  },

  async getStats(): Promise<Stats> {
    const response = await fetch(`${API_BASE_URL}/api/v1/stats`);
    if (!response.ok) {
      throw new Error('Failed to fetch stats');
    }
    return response.json();
  },

  async scheduleReferral(referralId: string, caregiverId?: string): Promise<any> {
    const queryParams = new URLSearchParams();
    queryParams.append('referral_id', referralId);
    if (caregiverId) {
      queryParams.append('caregiver_id', caregiverId);
    }

    const response = await fetch(
      `${API_BASE_URL}/api/v1/schedule/confirm?${queryParams}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
    
    if (!response.ok) {
      throw new Error('Failed to schedule referral');
    }
    return response.json();
  },

  async processReferralWithCrew(referralId: string): Promise<any> {
    const queryParams = new URLSearchParams();
    queryParams.append('referral_id', referralId);

    const response = await fetch(
      `${API_BASE_URL}/api/v1/crew/process-referral?${queryParams}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
    
    if (!response.ok) {
      throw new Error('Failed to process referral with Crew AI');
    }
    return response.json();
  },
};

