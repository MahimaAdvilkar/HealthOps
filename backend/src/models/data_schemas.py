from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


class CaregiverResponse(BaseModel):
    caregiver_id: str
    gender: Optional[str]
    date_of_birth: Optional[date]
    age: Optional[int]
    primary_language: Optional[str]
    skills: Optional[str]
    employment_type: Optional[str]
    availability: Optional[str]
    city: Optional[str]
    active: Optional[str]
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ReferralResponse(BaseModel):
    referral_id: str
    use_case: Optional[str]
    service_type: Optional[str]
    referral_source: Optional[str]
    urgency: Optional[str]
    referral_received_date: Optional[date]
    first_outreach_date: Optional[date]
    last_activity_date: Optional[date]
    insurance_active: Optional[str]
    payer: Optional[str]
    plan_type: Optional[str]
    auth_required: Optional[str]
    auth_status: Optional[str]
    auth_start_date: Optional[date]
    auth_end_date: Optional[date]
    auth_units_total: Optional[int]
    auth_units_remaining: Optional[int]
    unit_type: Optional[str]
    docs_complete: Optional[str]
    home_assessment_done: Optional[str]
    patient_responsive: Optional[str]
    contact_attempts: Optional[int]
    schedule_status: Optional[str]
    scheduled_date: Optional[date]
    units_scheduled_next_7d: Optional[int]
    units_delivered_to_date: Optional[int]
    service_complete: Optional[str]
    evv_or_visit_note_exists: Optional[str]
    ready_to_bill: Optional[str]
    claim_status: Optional[str]
    denial_reason: Optional[str]
    payment_amount: Optional[float]
    patient_dob: Optional[date]
    patient_age: Optional[int]
    patient_gender: Optional[str]
    patient_address: Optional[str]
    patient_city: Optional[str]
    patient_zip: Optional[str]
    agent_segment: Optional[str]
    agent_next_action: Optional[str]
    agent_rationale: Optional[str]
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DataStatsResponse(BaseModel):
    total_referrals: int
    active_referrals: int
    total_caregivers: int
    active_caregivers: int


class DashboardCard(BaseModel):
    title: str
    value: str


class FunnelStage(BaseModel):
    stage: str
    count: int


class DashboardMetricsResponse(BaseModel):
    cards: List[DashboardCard]
    funnel: List[FunnelStage]
