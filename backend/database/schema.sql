-- HealthOps PostgreSQL Database Schema
-- Created: 2026-01-10

-- Create database (run this separately if needed)
-- CREATE DATABASE healthops_db;

-- ============================================
-- REFERRALS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS referrals (
    referral_id VARCHAR(20) PRIMARY KEY,
    use_case VARCHAR(50),
    service_type VARCHAR(100),
    referral_source VARCHAR(100),
    urgency VARCHAR(20),
    referral_received_date DATE,
    first_outreach_date DATE,
    last_activity_date DATE,
    insurance_active CHAR(1),
    payer VARCHAR(100),
    plan_type VARCHAR(50),
    auth_required CHAR(1),
    auth_status VARCHAR(50),
    auth_start_date DATE,
    auth_end_date DATE,
    auth_units_total INTEGER,
    auth_units_remaining INTEGER,
    unit_type VARCHAR(20),
    docs_complete CHAR(1),
    home_assessment_done CHAR(1),
    patient_responsive VARCHAR(10),
    contact_attempts INTEGER,
    schedule_status VARCHAR(50),
    scheduled_date DATE,
    units_scheduled_next_7d INTEGER,
    units_delivered_to_date INTEGER,
    service_complete CHAR(1),
    evv_or_visit_note_exists CHAR(1),
    ready_to_bill CHAR(1),
    claim_status VARCHAR(50),
    denial_reason VARCHAR(100),
    payment_amount DECIMAL(10, 2),
    patient_dob DATE,
    patient_age INTEGER,
    patient_gender VARCHAR(20),
    patient_address TEXT,
    patient_city VARCHAR(100),
    patient_zip VARCHAR(10),
    agent_segment VARCHAR(20),
    agent_next_action VARCHAR(100),
    agent_rationale TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- CAREGIVERS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS caregivers (
    caregiver_id VARCHAR(20) PRIMARY KEY,
    gender VARCHAR(20),
    date_of_birth DATE,
    age INTEGER,
    primary_language VARCHAR(50),
    skills TEXT,
    employment_type VARCHAR(50),
    availability VARCHAR(50),
    city VARCHAR(100),
    active CHAR(1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- REFERRAL ASSIGNMENTS (PAIRING + SCHEDULING)
-- ============================================
CREATE TABLE IF NOT EXISTS referral_assignments (
    referral_id VARCHAR(20) PRIMARY KEY,
    caregiver_id VARCHAR(20),
    schedule_status VARCHAR(50) DEFAULT 'SCHEDULED',
    scheduled_date DATE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================
CREATE INDEX idx_referrals_patient_city ON referrals(patient_city);
CREATE INDEX idx_referrals_urgency ON referrals(urgency);
CREATE INDEX idx_referrals_agent_segment ON referrals(agent_segment);
CREATE INDEX idx_referrals_schedule_status ON referrals(schedule_status);
CREATE INDEX idx_referrals_received_date ON referrals(referral_received_date);
CREATE INDEX idx_referrals_payer ON referrals(payer);

CREATE INDEX idx_caregivers_city ON caregivers(city);
CREATE INDEX idx_caregivers_active ON caregivers(active);
CREATE INDEX idx_caregivers_skills ON caregivers(skills);
CREATE INDEX idx_caregivers_language ON caregivers(primary_language);

CREATE INDEX idx_referral_assignments_caregiver ON referral_assignments(caregiver_id);

-- ============================================
-- VIEWS FOR COMMON QUERIES
-- ============================================

-- Active referrals requiring action
CREATE OR REPLACE VIEW active_referrals AS
SELECT 
    referral_id,
    use_case,
    service_type,
    urgency,
    patient_city,
    agent_segment,
    agent_next_action,
    schedule_status,
    auth_units_remaining,
    contact_attempts
FROM referrals
WHERE service_complete = 'N'
ORDER BY urgency DESC, referral_received_date ASC;

-- Available caregivers by city and skills
CREATE OR REPLACE VIEW available_caregivers AS
SELECT 
    caregiver_id,
    gender,
    age,
    primary_language,
    skills,
    employment_type,
    availability,
    city
FROM caregivers
WHERE active = 'Y'
ORDER BY city, skills;

-- Referrals awaiting scheduling
CREATE OR REPLACE VIEW pending_scheduling AS
SELECT 
    referral_id,
    service_type,
    patient_city,
    urgency,
    auth_end_date,
    auth_units_remaining,
    contact_attempts,
    patient_responsive
FROM referrals
WHERE schedule_status = 'NOT_SCHEDULED'
  AND insurance_active = 'Y'
  AND auth_status = 'APPROVED'
ORDER BY urgency DESC, auth_end_date ASC;

-- Billing ready referrals
CREATE OR REPLACE VIEW ready_for_billing AS
SELECT 
    referral_id,
    service_type,
    payer,
    plan_type,
    units_delivered_to_date,
    payment_amount,
    claim_status
FROM referrals
WHERE ready_to_bill = 'Y'
  AND evv_or_visit_note_exists = 'Y'
  AND claim_status != 'PAID'
ORDER BY last_activity_date ASC;
