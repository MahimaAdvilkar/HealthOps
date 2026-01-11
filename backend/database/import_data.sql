-- Import data from CSV files into PostgreSQL
-- Run after creating schema.sql

-- ============================================
-- LOAD CAREGIVERS DATA
-- ============================================
\COPY caregivers(caregiver_id, gender, date_of_birth, age, primary_language, skills, employment_type, availability, city, active) FROM 'c:/projects/HealthOps/data/caregivers_synthetic.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

-- ============================================
-- LOAD REFERRALS DATA
-- ============================================
\COPY referrals(referral_id, use_case, service_type, referral_source, urgency, referral_received_date, first_outreach_date, last_activity_date, insurance_active, payer, plan_type, auth_required, auth_status, auth_start_date, auth_end_date, auth_units_total, auth_units_remaining, unit_type, docs_complete, home_assessment_done, patient_responsive, contact_attempts, schedule_status, scheduled_date, units_scheduled_next_7d, units_delivered_to_date, service_complete, evv_or_visit_note_exists, ready_to_bill, claim_status, denial_reason, payment_amount, patient_dob, patient_age, patient_gender, patient_address, patient_city, patient_zip, agent_segment, agent_next_action, agent_rationale) FROM 'c:/projects/HealthOps/data/referrals_synthetic.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

-- ============================================
-- VERIFY DATA LOADED
-- ============================================
SELECT 'Caregivers loaded:' as info, COUNT(*) as count FROM caregivers;
SELECT 'Referrals loaded:' as info, COUNT(*) as count FROM referrals;

-- Sample queries to verify
SELECT * FROM caregivers LIMIT 5;
SELECT * FROM referrals LIMIT 5;
