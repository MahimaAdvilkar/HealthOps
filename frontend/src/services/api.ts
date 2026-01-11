const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8022';

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

export interface DashboardCard {
  title: string;
  value: string;
}

export interface FunnelStage {
  stage: string;
  count: number;
}

export interface DashboardMetrics {
  cards: DashboardCard[];
  funnel: FunnelStage[];
}

export interface OpsSummaryKpis {
  total_referrals: number;
  active_clients: number;
  completed_clients: number;
  scheduled_clients: number;
  pending_scheduling: number;
  total_caregivers: number;
  active_caregivers: number;
  available_caregivers?: number;
  busy_caregivers?: number;
  paired_referrals: number;
  unique_caregivers_paired: number;
  leads_last_7d: number;
  leads_last_7d_urgent: number;
  urgent_pending: number;
}

export interface OpsUrgentPreviewItem {
  referral_id: string;
  patient_city?: string;
  agent_segment?: string;
  auth_units_remaining?: number;
  referral_received_date?: string;
}

export interface OpsPriorityItem {
  referral_id: string;
  urgency?: string;
  agent_segment?: string;
  patient_city?: string;
  payer?: string;
  schedule_status?: string;
  auth_units_remaining?: number;
  contact_attempts?: number;
  referral_received_date?: string;
  score: number;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface OpsSummary {
  kpis: OpsSummaryKpis;
  urgent_pending_preview: OpsUrgentPreviewItem[];
  priority_queue: OpsPriorityItem[];
  generated_at: string;
}

export interface IntakeSimulateResponse {
  success: boolean;
  mode: 'db' | 'file';
  referral: Referral;
}

export interface PdfIntakeCreatedItem {
  referral: Referral;
  source_filename: string;
  classification?: {
    type: 'referral' | 'compliance' | 'other';
    confidence: number;
    reasons: string[];
  };
  landingai?: {
    processing_time?: number;
    metadata?: Record<string, any>;
  };
}

export interface PdfIntakeResponse {
  success: boolean;
  mode: 'db' | 'file';
  created: PdfIntakeCreatedItem[];
  compliance_saved?: Array<{
    compliance_id: string;
    source_filename: string;
    classification: { type: 'compliance'; confidence: number; reasons: string[] };
  }>;
  ignored?: Array<{
    source_filename: string;
    classification: { type: 'referral' | 'compliance' | 'other'; confidence: number; reasons: string[] };
  }>;
  errors: Array<{ filename: string; error: string }>;
}

export interface ComplianceDoc {
  compliance_id: string;
  source_filename: string;
  created_at: string;
  excerpt?: string;
  classification?: any;
}

export interface ComplianceDocsResponse {
  success: boolean;
  count: number;
  docs: ComplianceDoc[];
  generated_at: string;
}

export interface ReferralJourneyEvent {
  stage: string;
  at?: string;
  source?: string;
  note?: string;
}

export interface ReferralJourneyResponse {
  success: boolean;
  referral_id: string;
  current_stage: string;
  timeline: ReferralJourneyEvent[];
  updated_at?: string;
}

export interface JourneyBoardReferral {
  referral_id: string;
  urgency?: string;
  agent_segment?: string;
  patient_city?: string;
  payer?: string;
  schedule_status?: string;
  auth_status?: string;
  agent_next_action?: string;
  referral_received_date?: string;
}

export interface JourneyBoardStage {
  stage: string;
  label: string;
  count: number;
  referrals: JourneyBoardReferral[];
}

export interface JourneyBoardResponse {
  success: boolean;
  stages: JourneyBoardStage[];
  generated_at: string;
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

  // Legacy/optional endpoints (kept for compatibility with main branch features)
  async scheduleReferral(referralId: string, caregiverId?: string): Promise<any> {
    const queryParams = new URLSearchParams();
    queryParams.append('referral_id', referralId);
    if (caregiverId) queryParams.append('caregiver_id', caregiverId);

    const response = await fetch(`${API_BASE_URL}/api/v1/schedule/confirm?${queryParams.toString()}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) throw new Error('Failed to schedule referral');
    return response.json();
  },

  async processReferralWithCrew(referralId: string): Promise<any> {
    const queryParams = new URLSearchParams();
    queryParams.append('referral_id', referralId);

    const response = await fetch(`${API_BASE_URL}/api/v1/crew/process-referral?${queryParams.toString()}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) throw new Error('Failed to process referral with Crew AI');
    return response.json();
  },

  async getDashboardMetrics(): Promise<DashboardMetrics> {
    const response = await fetch(`${API_BASE_URL}/api/v1/dashboard-metrics`);
    if (!response.ok) {
      throw new Error('Failed to fetch dashboard metrics');
    }
    return response.json();
  },

  async getOpsSummary(params?: { limit?: number }): Promise<OpsSummary> {
    const queryParams = new URLSearchParams();
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    const qs = queryParams.toString();

    const response = await fetch(`${API_BASE_URL}/api/v1/ops/summary${qs ? `?${qs}` : ''}`);
    if (!response.ok) {
      throw new Error('Failed to fetch ops summary');
    }
    return response.json();
  },

  async simulateIntake(params?: {
    urgency?: string;
    patient_city?: string;
    payer?: string;
    service_type?: string;
  }): Promise<IntakeSimulateResponse> {
    const queryParams = new URLSearchParams();
    if (params?.urgency) queryParams.append('urgency', params.urgency);
    if (params?.patient_city) queryParams.append('patient_city', params.patient_city);
    if (params?.payer) queryParams.append('payer', params.payer);
    if (params?.service_type) queryParams.append('service_type', params.service_type);
    const qs = queryParams.toString();

    const response = await fetch(`${API_BASE_URL}/api/v1/intake/simulate${qs ? `?${qs}` : ''}`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error('Failed to simulate intake');
    }
    return response.json();
  },

  async intakeFromPdf(files: File[]): Promise<PdfIntakeResponse> {
    const form = new FormData();
    files.forEach((f) => form.append('files', f));

    const response = await fetch(`${API_BASE_URL}/api/v1/intake/from-pdf`, {
      method: 'POST',
      body: form,
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || 'Failed to intake PDFs');
    }
    return response.json();
  },

  async getComplianceDocs(params?: { limit?: number }): Promise<ComplianceDocsResponse> {
    const queryParams = new URLSearchParams();
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    const qs = queryParams.toString();
    const response = await fetch(`${API_BASE_URL}/api/v1/compliance/docs${qs ? `?${qs}` : ''}`);
    if (!response.ok) throw new Error('Failed to fetch compliance docs');
    return response.json();
  },

  async getReferralJourney(referralId: string): Promise<ReferralJourneyResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/referrals/${encodeURIComponent(referralId)}/journey`);
    if (!response.ok) throw new Error('Failed to fetch referral journey');
    return response.json();
  },

  async advanceReferralJourney(referralId: string, stage: string, note?: string): Promise<any> {
    const queryParams = new URLSearchParams();
    queryParams.append('stage', stage);
    if (note) queryParams.append('note', note);
    const response = await fetch(
      `${API_BASE_URL}/api/v1/referrals/${encodeURIComponent(referralId)}/journey/advance?${queryParams.toString()}`,
      { method: 'POST' }
    );
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || 'Failed to advance referral journey');
    }
    return response.json();
  },

  async getJourneyBoard(params?: { limitPerStage?: number }): Promise<JourneyBoardResponse> {
    const queryParams = new URLSearchParams();
    if (params?.limitPerStage) queryParams.append('limit_per_stage', params.limitPerStage.toString());
    const qs = queryParams.toString();
    const response = await fetch(`${API_BASE_URL}/api/v1/journey/board${qs ? `?${qs}` : ''}`);
    if (!response.ok) throw new Error('Failed to fetch journey board');
    return response.json();
  },
};

