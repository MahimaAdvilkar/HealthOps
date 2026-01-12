-- Migration: Add journey_stage columns to referrals table
-- Run this to update an existing database

ALTER TABLE referrals 
ADD COLUMN IF NOT EXISTS journey_stage VARCHAR(50) DEFAULT 'INTAKE_RECEIVED';

ALTER TABLE referrals 
ADD COLUMN IF NOT EXISTS journey_updated_at TIMESTAMP;

-- Update existing referrals to have a journey stage based on their current status
UPDATE referrals 
SET journey_stage = CASE 
    WHEN service_complete = 'Y' THEN 'SERVICE_COMPLETED'
    WHEN ready_to_bill = 'Y' THEN 'READY_TO_BILL'
    WHEN schedule_status = 'SCHEDULED' THEN 'SCHEDULED'
    WHEN home_assessment_done = 'Y' THEN 'HOME_ASSESSMENT_COMPLETED'
    WHEN docs_complete = 'Y' THEN 'DOCS_COMPLETED'
    ELSE 'INTAKE_RECEIVED'
END,
journey_updated_at = CURRENT_TIMESTAMP
WHERE journey_stage IS NULL OR journey_stage = '';

-- Create index for journey stage queries
CREATE INDEX IF NOT EXISTS idx_referrals_journey_stage ON referrals(journey_stage);
