import csv
import random
from datetime import date, datetime, timedelta

NUM_REFERRALS = 1000

use_cases = ["HOME_CARE", "IMAGING"]
service_types_home = ["ECM", "PersonalCare", "HomeHealthNursing", "HomeHealthPT", "BehavioralHealth", "CS_HousingSupport", "CS_NutritionSupport"]
service_types_img = ["MRI_KNEE", "CT_ABDOMEN", "MRI_BRAIN", "XRAY_CHEST", "MRI_SPINE", "ULTRASOUND_ABD", "MAMMOGRAM", "MRI_SHOULDER", "CT_HEAD", "MRI_LUMBAR"]

referral_sources = ["PCP", "Hospital", "County", "Payer", "Self"]
urgencies = ["Routine", "Urgent"]

payers = ["BlueCross", "Aetna", "United", "Medicare", "Cigna", "Anthem", "Medi-Cal"]
plan_types = ["PPO", "HMO", "POS", "FFS", "Commercial", "ManagedCare", "Medicaid"]

cities = ["San Francisco", "Oakland", "San Jose", "Fremont", "Dublin", "Berkeley", "San Leandro"]
streets = ["Market St", "Mission St", "Geary Blvd", "Broadway", "International Blvd", "Foothill Blvd", "University Ave"]
genders = ["Female", "Male", "Other"]

# ---- helpers ----
def rand_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))

def rand_datetime_iso(start: date, end: date) -> str:
    d = rand_date(start, end)
    # keep it date-only ISO for simplicity in CSV
    return d.isoformat()

def random_dob():
    start = date(1940, 1, 1)
    end = date(2006, 12, 31)
    return rand_date(start, end)

def compute_age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

def maybe(p=0.5):
    return random.random() < p

def choose_service_type(use_case: str) -> str:
    return random.choice(service_types_home) if use_case == "HOME_CARE" else random.choice(service_types_img)

def pick_unit_type(use_case: str) -> str:
    # imaging is usually SCANS, home care HOURS/VISITS
    if use_case == "IMAGING":
        return "SCANS"
    return random.choice(["HOURS", "VISITS"])

def auth_logic(payer: str, plan_type: str, use_case: str) -> str:
    # simple heuristic: many imaging requires auth, Medicare FFS often not required
    if payer == "Medicare" and plan_type == "FFS":
        return "N"
    if use_case == "IMAGING":
        return "Y" if maybe(0.75) else "N"
    return "Y" if maybe(0.85) else "N"

def auth_status_logic(auth_required: str) -> str:
    if auth_required == "N":
        return "NOT_REQUIRED"
    r = random.random()
    if r < 0.60:
        return "APPROVED"
    if r < 0.85:
        return "PENDING"
    if r < 0.95:
        return "DENIED"
    return "EXPIRED"

def agent_segment_logic(row) -> str:
    # GREEN: ready to move, YELLOW: waiting, ORANGE: at risk, RED: blocked
    if row["insurance_active"] == "N":
        return "RED"
    if row["auth_required"] == "Y" and row["auth_status"] in ["DENIED", "EXPIRED"]:
        return "RED"
    if row["auth_required"] == "Y" and row["auth_status"] == "PENDING":
        return "YELLOW"
    # at-risk if auth end is close and not scheduled
    if row["auth_end_date"] and row["schedule_status"] == "NOT_SCHEDULED":
        try:
            end = datetime.strptime(row["auth_end_date"], "%Y-%m-%d").date()
            if (end - date.today()).days <= 5:
                return "ORANGE"
        except:
            pass
    if row["docs_complete"] == "N" or row["home_assessment_done"] == "N":
        return "ORANGE"
    return "GREEN"

def next_action_logic(segment: str, row) -> str:
    if segment == "RED":
        return "HOLD"
    if segment == "YELLOW":
        return "FOLLOW_UP_AUTH"
    if segment == "ORANGE":
        if row["docs_complete"] == "N":
            return "REQUEST_DOCS"
        return "ESCALATE"
    # GREEN
    if row["schedule_status"] in ["NOT_SCHEDULED"]:
        return "SCHEDULE_NOW"
    if row["schedule_status"] in ["SCHEDULED"] and row["ready_to_bill"] == "N":
        return "MONITOR_SERVICE"
    return "BILL_NOW"

def rationale_logic(action: str, row) -> str:
    if action == "HOLD":
        if row["insurance_active"] == "N":
            return "Insurance inactive; block workflow until eligibility is resolved."
        if row["auth_status"] in ["DENIED", "EXPIRED"]:
            return f"Auth {row['auth_status'].lower()}; stop scheduling and route to appeal/new auth."
        return "Blocked state; needs manual review."
    if action == "FOLLOW_UP_AUTH":
        return "Auth required and pending; follow up with payer and keep patient warm."
    if action == "REQUEST_DOCS":
        return "Missing docs/packets needed for downstream scheduling/billing; request immediately."
    if action == "ESCALATE":
        return "At risk of delay (stale lead, short auth window, low responsiveness); escalate for action today."
    if action == "SCHEDULE_NOW":
        return "All checks passed; schedule within authorization window and match capacity."
    if action == "MONITOR_SERVICE":
        return "Service in progress; track delivered units and ensure visit notes/EVV captured."
    if action == "BILL_NOW":
        return "Service complete and documentation present; ready to submit claim."
    return "System generated."

# ---- generate ----
random.seed(42)

start_window = date(2025, 12, 1)
end_window = date(2026, 1, 10)

rows = []
for n in range(1, NUM_REFERRALS + 1):
    referral_id = f"REF-{1000+n}"

    use_case = random.choice(use_cases)
    service_type = choose_service_type(use_case)
    referral_source = random.choice(referral_sources)
    urgency = random.choice(urgencies)

    referral_received_date = rand_date(start_window, end_window)
    first_outreach_date = referral_received_date + timedelta(days=random.randint(0, 5))
    last_activity_date = first_outreach_date + timedelta(days=random.randint(0, 10))

    insurance_active = "Y" if maybe(0.88) else "N"
    payer = random.choice(payers)
    plan_type = random.choice(plan_types)

    auth_required = auth_logic(payer, plan_type, use_case)
    auth_status = auth_status_logic(auth_required)

    # auth dates
    auth_start_date = ""
    auth_end_date = ""
    if auth_required == "Y" and auth_status in ["APPROVED", "PENDING", "DENIED", "EXPIRED"]:
        auth_start_date = (referral_received_date + timedelta(days=random.randint(0, 5))).isoformat()
        # shorter windows for imaging
        window_days = random.randint(7, 25) if use_case == "IMAGING" else random.randint(14, 90)
        auth_end_date = (datetime.strptime(auth_start_date, "%Y-%m-%d").date() + timedelta(days=window_days)).isoformat()

    unit_type = pick_unit_type(use_case)
    if unit_type == "SCANS":
        auth_units_total = 1
    elif unit_type == "VISITS":
        auth_units_total = random.choice([8, 12, 16, 24])
    else:
        auth_units_total = random.choice([20, 30, 40, 50, 60, 80])

    used_units = random.randint(0, max(0, auth_units_total - 1))
    auth_units_remaining = auth_units_total - used_units

    docs_complete = "Y" if maybe(0.72) else "N"
    home_assessment_done = "Y" if (use_case == "HOME_CARE" and maybe(0.65)) else "N"
    patient_responsive = random.choice(["HIGH", "MED", "LOW"])
    contact_attempts = random.randint(0, 7)

    # scheduling status logic
    schedule_status = random.choice(["NOT_SCHEDULED", "SCHEDULED", "COMPLETED"])
    scheduled_date = ""
    if schedule_status in ["SCHEDULED", "COMPLETED"]:
        scheduled_date = (referral_received_date + timedelta(days=random.randint(1, 14))).isoformat()

    units_scheduled_next_7d = random.randint(0, 15) if use_case == "HOME_CARE" else random.randint(0, 1)
    units_delivered_to_date = used_units

    # billing
    service_complete = "Y" if schedule_status == "COMPLETED" else "N"
    evv_or_visit_note_exists = "Y" if (service_complete == "Y" and maybe(0.85)) else "N"
    ready_to_bill = "Y" if (service_complete == "Y" and evv_or_visit_note_exists == "Y") else "N"

    claim_status = "NOT_SUBMITTED"
    denial_reason = ""
    payment_amount = 0

    if ready_to_bill == "Y":
        claim_status = random.choice(["SUBMITTED", "PENDED", "PAID"])
        if claim_status == "PAID":
            # rough payments
            if use_case == "IMAGING":
                payment_amount = random.choice([250, 400, 650, 900, 1200])
            else:
                payment_amount = random.choice([500, 800, 1200, 2000, 3500])
        elif claim_status == "PENDED":
            denial_reason = random.choice(["Missing_Doc", "Coding_Issue", "Eligibility_Review", "Auth_Mismatch"])

    # patient demographics
    dob = random_dob()
    patient_age = compute_age(dob)
    patient_gender = random.choice(genders)
    city = random.choice(cities)
    zip_code = str(random.randint(94000, 95199))
    address = f"{random.randint(100, 9999)} {random.choice(streets)}, {city}, CA {zip_code}"

    row = {
        # core referral fields
        "referral_id": referral_id,
        "use_case": use_case,
        "service_type": service_type,
        "referral_source": referral_source,
        "urgency": urgency,
        "referral_received_date": referral_received_date.isoformat(),
        "first_outreach_date": first_outreach_date.isoformat(),
        "last_activity_date": last_activity_date.isoformat(),
        "insurance_active": insurance_active,
        "payer": payer,
        "plan_type": plan_type,
        "auth_required": auth_required,
        "auth_status": auth_status,
        "auth_start_date": auth_start_date,
        "auth_end_date": auth_end_date,
        "auth_units_total": auth_units_total,
        "auth_units_remaining": auth_units_remaining,
        "unit_type": unit_type,
        "docs_complete": docs_complete,
        "home_assessment_done": home_assessment_done,
        "patient_responsive": patient_responsive,
        "contact_attempts": contact_attempts,
        "schedule_status": schedule_status,
        "scheduled_date": scheduled_date,
        "units_scheduled_next_7d": units_scheduled_next_7d,
        "units_delivered_to_date": units_delivered_to_date,

        # service -> billing bridge
        "service_complete": service_complete,
        "evv_or_visit_note_exists": evv_or_visit_note_exists,
        "ready_to_bill": ready_to_bill,
        "claim_status": claim_status,
        "denial_reason": denial_reason,
        "payment_amount": payment_amount,

        # patient demographics
        "patient_dob": dob.isoformat(),
        "patient_age": patient_age,
        "patient_gender": patient_gender,
        "patient_address": address,
        "patient_city": city,
        "patient_zip": zip_code
    }

    # agent columns at end (computed off row)
    row["agent_segment"] = agent_segment_logic(row)
    row["agent_next_action"] = next_action_logic(row["agent_segment"], row)
    row["agent_rationale"] = rationale_logic(row["agent_next_action"], row)

    rows.append(row)

output_path = "data/referrals_synthetic.csv"

with open(output_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"Generated {NUM_REFERRALS} referrals → {output_path}")

