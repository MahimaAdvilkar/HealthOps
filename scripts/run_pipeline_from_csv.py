from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from src.services.pipeline_utils import apply_agent_result
from src.services.pipeline_states import PipelineState
from src.services.agents.referral_received_agent import ReferralReceivedAgent
from src.services.agents.intake_complete_agent import IntakeCompleteAgent
from src.services.agents.assessment_complete_agent import AssessmentCompleteAgent
from src.services.agents.eligibility_verified_agent import EligibilityVerifiedAgent
from src.services.agents.auth_pending_agent import AuthPendingAgent
from src.services.agents.auth_approved_agent import AuthApprovedAgent
from src.services.agents.ready_to_schedule_agent import ReadyToScheduleAgent

REFERRALS_CSV = "data/referrals_synthetic.csv"
CAREGIVERS_CSV = "data/caregivers_synthetic.csv"
OUT_CSV = "data/documents/extracted/pipeline_outcomes.csv"


def read_csv_dicts(path: str) -> List[Dict[str, str]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def normalize_from_row(row: Dict[str, str]) -> Dict[str, Any]:
    # Map synthetic referral columns into our normalized shape
    norm: Dict[str, Any] = {
        "referral_id": row.get("referral_id"),
        "patient_name": row.get("patient_name"),  # may be missing in dataset
        "date_of_birth": row.get("patient_dob"),
        "payer": row.get("payer"),
        "plan_type": row.get("plan_type"),
        "authorization_required": row.get("auth_required"),
        "authorization_status": row.get("auth_status"),
        "authorization_number": row.get("auth_number") or row.get("authorization_number"),
        "authorization_start_date": row.get("auth_start_date"),
        "authorization_end_date": row.get("auth_end_date"),
        "authorized_units": row.get("auth_units_total"),
        "units_used": row.get("auth_units_remaining"),
        "units_delivered": row.get("units_delivered_to_date"),
        "unit_type": row.get("unit_type"),
        "service_category": row.get("use_case"),
        "procedure": row.get("service_type"),
        "date_of_service": row.get("scheduled_date"),
        "ready_to_bill": row.get("ready_to_bill"),
        "billing_hold_reason": row.get("denial_reason"),
        "facility": row.get("facility"),
        "city": row.get("patient_city"),
        "technician_name": row.get("technician_name"),
        "signed_date": row.get("referral_received_date"),
        "issued_date": row.get("first_outreach_date"),
        "issued_by": row.get("referral_source"),
        # Patient contact
        "patient_address": row.get("patient_address"),
        "patient_city": row.get("patient_city"),
        "patient_zip": row.get("patient_zip"),
        "patient_phone": row.get("patient_phone"),
    }
    return norm


def match_caregiver(row: Dict[str, str], caregivers: List[Dict[str, str]]) -> str | None:
    """Simple matcher: prefer same city and skill matches procedure/service_type."""
    target_city = (row.get("patient_city") or "").strip().lower()
    proc = (row.get("service_type") or "").strip().lower()

    best_id = None
    best_score = -1
    for cg in caregivers:
        if (cg.get("active") or "Y").strip().upper() != "Y":
            continue
        score = 0
        if (cg.get("city") or "").strip().lower() == target_city:
            score += 2
        skills = (cg.get("skills") or "").strip().lower()
        if skills and proc and proc.split("_")[0] in skills:
            score += 2
        elif skills and (row.get("use_case") or "").strip().lower() in skills:
            score += 1
        if score > best_score:
            best_score = score
            best_id = cg.get("caregiver_id")
    return best_id


def run_for_row(row: Dict[str, str], caregivers: List[Dict[str, str]]) -> Dict[str, Any]:
    # Build context and apply normalized patch
    context: Dict[str, Any] = {
        "case_id": row.get("referral_id"),
        "state": PipelineState.REFERRAL_RECEIVED.value,
        "decisions": {},
        "actions": [],
        "normalized": {},
    }
    apply_agent_result(context, {"normalized_patch": normalize_from_row(row)})

    # Run pipeline agents (skip extraction/normalizer since data is already normalized)
    agents = [
        ReferralReceivedAgent(),
        IntakeCompleteAgent(),
        AssessmentCompleteAgent(),
        EligibilityVerifiedAgent(),
        AuthPendingAgent(),
        AuthApprovedAgent(),
        ReadyToScheduleAgent(),
    ]

    for a in agents:
        r = a.run(context)
        apply_agent_result(context, r.data)
        if not r.success:
            break

    # Caregiver match if ready to schedule
    matched_cg = None
    if context.get("decisions", {}).get("ready_to_schedule"):
        matched_cg = match_caregiver(row, caregivers)

    return {
        "referral_id": row.get("referral_id"),
        "state": context.get("state"),
        "referral_received": context.get("decisions", {}).get("referral_received"),
        "intake_complete": context.get("decisions", {}).get("intake_complete"),
        "assessment_complete": context.get("decisions", {}).get("assessment_complete"),
        "eligibility_verified": context.get("decisions", {}).get("eligibility_verified"),
        "auth_required": context.get("decisions", {}).get("auth_required"),
        "auth_planned": context.get("decisions", {}).get("auth_planned"),
        "auth_approved": context.get("decisions", {}).get("auth_approved"),
        "ready_to_schedule": context.get("decisions", {}).get("ready_to_schedule"),
        "matched_caregiver_id": matched_cg or "",
    }


def write_csv(path: str, rows: List[Dict[str, Any]]):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    referrals = read_csv_dicts(REFERRALS_CSV)
    caregivers = read_csv_dicts(CAREGIVERS_CSV)
    print(f"Loaded {len(referrals)} referrals and {len(caregivers)} caregivers.")

    outcomes: List[Dict[str, Any]] = []
    for idx, row in enumerate(referrals):
        out = run_for_row(row, caregivers)
        outcomes.append(out)
        if idx < 3:
            print("Debug sample:", out)

    write_csv(OUT_CSV, outcomes)
    print(f"Wrote outcomes: {OUT_CSV}")
    # Quick summary
    ready = sum(1 for r in outcomes if r.get("ready_to_schedule"))
    matched = sum(1 for r in outcomes if r.get("matched_caregiver_id"))
    print(f"Ready to schedule: {ready} / {len(outcomes)}")
    print(f"Caregiver matched: {matched} / {len(outcomes)}")


if __name__ == "__main__":
    main()
