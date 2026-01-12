from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Response
from fastapi.responses import HTMLResponse
from starlette.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List, Optional
import sys
from pathlib import Path
import base64
import csv
from datetime import datetime, date, timedelta
import json
import random

sys.path.insert(0, str(Path(__file__).parent))

from src.models.schemas import ImageRequest, ImageResponse, ErrorResponse
from src.models.data_schemas import (
    CaregiverResponse,
    ReferralResponse,
    DataStatsResponse,
    DashboardMetricsResponse,
)
from src.services.landingai_service import LandingAIService
from src.services.agent_workflow import AgentWorkflow
from src.services.crew_workflow import HealthOpsCrewWorkflow
from src.services.email_service import email_service
from src.services.rules_engine import rules_engine
from src.services.sorting_agent import sorting_agent
from database.db_service import DatabaseService


landingai_service = None
db_service = None
agent_workflow = None
crew_workflow = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global landingai_service, db_service, agent_workflow, crew_workflow
    try:
        landingai_service = LandingAIService()
        print("Landing AI service initialized successfully")
    except Exception as e:
        landingai_service = None
        print(f"Warning: Landing AI service not initialized - {e}")
    
    db_service = DatabaseService()
    result = db_service.connect()
    if result['success']:
        print("Database service initialized successfully")
    else:
        print(f"Warning: Database connection failed - {result['message']}")
    
    agent_workflow = AgentWorkflow()
    print("Agent Workflow initialized successfully")
    
    try:
        crew_workflow = HealthOpsCrewWorkflow()
        print("Crew AI Workflow initialized successfully")
    except Exception as e:
        print(f"Warning: Crew AI initialization failed - {e}")
        crew_workflow = None
    
    yield
    
    if db_service:
        db_service.disconnect()
    print("Shutting down...")


app = FastAPI(
    title="HealthOps API",
    description="Landing AI-powered medical image processing for healthcare operations",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "HealthOps API - Landing AI Image Processing",
        "status": "active",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "landingai_image_processor"
    }


# --- Simple Frontend Views for Document Tables ---

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC_EXTRACT_DIR = REPO_ROOT / "data" / "documents" / "extracted"
STATIC_DIR = Path(__file__).resolve().parent / "static"

DATA_DIR = REPO_ROOT / "data"
REFERRALS_CSV = DATA_DIR / "referrals_synthetic.csv"
CAREGIVERS_CSV = DATA_DIR / "caregivers_synthetic.csv"

SCHEDULING_OVERRIDES_PATH = DATA_DIR / "scheduling_overrides.json"
REFERRALS_RUNTIME_PATH = DATA_DIR / "referrals_runtime.json"
COMPLIANCE_DOCS_PATH = DATA_DIR / "compliance_runtime.json"
JOURNEY_OVERRIDES_PATH = DATA_DIR / "journey_overrides.json"

# Demo autopilot settings (kept simple and deterministic for showcase)
AUTOPILOT_ENABLED = True
AUTOPILOT_HOME_ASSESSMENT_DELAY_SEC = 25
AUTOPILOT_READY_TO_BILL_DELAY_SEC = 25
AUTOPILOT_COMPLETE_DELAY_SEC = 25


def _safe_date(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        s = str(value).strip()
        if not s:
            return None
        # ISO date like 2026-01-11
        return date.fromisoformat(s[:10])
    except Exception:
        return None


def _load_scheduling_overrides() -> dict:
    try:
        if not SCHEDULING_OVERRIDES_PATH.exists():
            return {}
        with open(SCHEDULING_OVERRIDES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_scheduling_overrides(overrides: dict) -> None:
    SCHEDULING_OVERRIDES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SCHEDULING_OVERRIDES_PATH, "w", encoding="utf-8") as f:
        json.dump(overrides, f, indent=2, ensure_ascii=False)


def _apply_scheduling_overrides(row: dict) -> dict:
    """Merge locally persisted scheduling updates into a referral row (CSV fallback mode)."""
    try:
        overrides = _load_scheduling_overrides()
        rid = str(row.get("referral_id") or "").strip()
        if not rid:
            return row
        o = overrides.get(rid)
        if not isinstance(o, dict):
            return row

        # Standardize fields used by the UI
        if o.get("schedule_status"):
            row["schedule_status"] = o.get("schedule_status")
        if o.get("scheduled_date"):
            row["scheduled_date"] = o.get("scheduled_date")
        if o.get("assigned_caregiver_id"):
            row["assigned_caregiver_id"] = o.get("assigned_caregiver_id")
        return row
    except Exception:
        return row


def _load_journey_overrides() -> dict:
    try:
        if not JOURNEY_OVERRIDES_PATH.exists():
            return {}
        with open(JOURNEY_OVERRIDES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_journey_overrides(overrides: dict) -> None:
    JOURNEY_OVERRIDES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JOURNEY_OVERRIDES_PATH, "w", encoding="utf-8") as f:
        json.dump(overrides, f, indent=2, ensure_ascii=False)


def _apply_journey_overrides(row: dict) -> dict:
    """Merge persisted journey events into a referral row (CSV fallback mode)."""
    try:
        rid = str(row.get("referral_id") or "").strip()
        if not rid:
            return row

        overrides = _load_journey_overrides()
        entry = overrides.get(rid)
        if not isinstance(entry, dict):
            return row
        events = entry.get("events")
        if not isinstance(events, list) or not events:
            return row

        # Apply events in order; later events win
        for ev in events:
            if not isinstance(ev, dict):
                continue
            stage = str(ev.get("stage") or "").strip().upper()
            if not stage:
                continue

            if stage == "DOCS_COMPLETED":
                row["docs_complete"] = "Y"
                row["agent_next_action"] = "Schedule home assessment"
            elif stage == "HOME_ASSESSMENT_SCHEDULED":
                row["agent_next_action"] = "Complete home assessment"
            elif stage == "HOME_ASSESSMENT_COMPLETED":
                row["home_assessment_done"] = "Y"
                row["agent_next_action"] = "Run AI scheduler"
            elif stage == "SERVICE_STARTED":
                row["agent_next_action"] = "Deliver authorized units"
            elif stage == "READY_TO_BILL":
                row["ready_to_bill"] = "Y"
                row["agent_next_action"] = "Submit claim"
            elif stage == "SERVICE_COMPLETED":
                row["service_complete"] = "Y"
                row["schedule_status"] = "COMPLETED"
                row["agent_next_action"] = "Completed"

        row["journey_current_stage"] = str(entry.get("current_stage") or "")
        row["journey_updated_at"] = str(entry.get("updated_at") or "")
        return row
    except Exception:
        return row


def _parse_iso_datetime(s: str) -> Optional[datetime]:
    try:
        if not s:
            return None
        ss = str(s).strip()
        if not ss:
            return None
        # Allow trailing Z
        if ss.endswith("Z"):
            ss = ss[:-1]
        return datetime.fromisoformat(ss)
    except Exception:
        return None


def _record_journey_event(rid: str, stage: str, source: str = "system", note: str = "") -> None:
    """Append a journey event (deduped by stage) in file mode store."""
    try:
        rid = str(rid or "").strip()
        st = str(stage or "").strip().upper()
        if not rid or not st:
            return
        overrides = _load_journey_overrides()
        entry = overrides.get(rid)
        if not isinstance(entry, dict):
            entry = {"events": []}
        events = entry.get("events")
        if not isinstance(events, list):
            events = []

        # If stage already exists, don't add again
        if any(isinstance(ev, dict) and str(ev.get("stage") or "").strip().upper() == st for ev in events):
            entry["current_stage"] = st
            entry["updated_at"] = datetime.utcnow().isoformat() + "Z"
            overrides[rid] = entry
            _save_journey_overrides(overrides)
            return

        ev = {
            "stage": st,
            "at": datetime.utcnow().isoformat() + "Z",
            "source": source,
            "note": (note or "").strip(),
        }
        events.append(ev)
        entry["events"] = events
        entry["current_stage"] = st
        entry["updated_at"] = ev["at"]
        overrides[rid] = entry
        _save_journey_overrides(overrides)
    except Exception:
        return


def _select_available_caregiver(referral: dict, caregivers: list[dict], assignments: dict, referrals: list[dict]) -> Optional[str]:
    """Pick an active caregiver with available capacity, preferring same city."""
    try:
        city = str(referral.get("patient_city") or "").strip()
        load = _compute_caregiver_load(assignments, referrals)

        def ok(c: dict) -> bool:
            if str(c.get("active") or "").strip().upper() != "Y":
                return False
            cg_id = str(c.get("caregiver_id") or "").strip()
            if not cg_id:
                return False
            cap = _caregiver_capacity(c)
            used = load.get(cg_id, 0)
            return used < cap

        same_city = [c for c in caregivers if ok(c) and str(c.get("city") or "").strip() == city]
        if same_city:
            return str(same_city[0].get("caregiver_id"))
        any_city = [c for c in caregivers if ok(c)]
        if any_city:
            return str(any_city[0].get("caregiver_id"))
        return None
    except Exception:
        return None


def _autopilot_should_run(referral: dict) -> bool:
    src = str(referral.get("intake_source") or "").strip().upper()
    if src in ("PDF", "SIMULATED"):
        return True
    # Legacy created rows
    rationale = str(referral.get("agent_rationale") or "").lower()
    if "ingested from pdf" in rationale or "demo" in rationale:
        return True
    return False


def _autopilot_tick_for_referral(referral: dict) -> None:
    """Automatic journey progression + optional auto-scheduling (file mode only)."""
    try:
        if not AUTOPILOT_ENABLED:
            return
        if not isinstance(referral, dict):
            return
        rid = str(referral.get("referral_id") or "").strip()
        if not rid:
            return
        if not _autopilot_should_run(referral):
            return
        if str(referral.get("service_complete") or "").strip().upper() == "Y":
            _record_journey_event(rid, "SERVICE_COMPLETED", source="autopilot")
            return

        # Always ensure intake event
        _record_journey_event(rid, "INTAKE_RECEIVED", source="autopilot")

        # Docs completion heuristic for runtime referrals: LandingAI parse implies docs exist
        if str(referral.get("docs_complete") or "").strip().upper() != "Y":
            _record_journey_event(rid, "DOCS_COMPLETED", source="autopilot", note="Docs inferred from intake")

        # If auth is required and not approved, stop at auth pending
        insurance_ok = str(referral.get("insurance_active") or "").strip().upper() == "Y"
        auth_required = str(referral.get("auth_required") or "").strip().upper() == "Y"
        auth_status = str(referral.get("auth_status") or "").strip().upper()
        if insurance_ok and auth_required and auth_status != "APPROVED":
            _record_journey_event(rid, "AUTH_PENDING", source="autopilot")
            return

        # Home assessment schedule/complete
        overrides = _load_journey_overrides()
        entry = overrides.get(rid) if isinstance(overrides, dict) else None
        entry = entry if isinstance(entry, dict) else {"events": []}
        events = entry.get("events") if isinstance(entry.get("events"), list) else []

        def has_stage(st: str) -> Optional[dict]:
            for ev in events:
                if isinstance(ev, dict) and str(ev.get("stage") or "").strip().upper() == st:
                    return ev
            return None

        if not has_stage("HOME_ASSESSMENT_SCHEDULED"):
            _record_journey_event(rid, "HOME_ASSESSMENT_SCHEDULED", source="autopilot")
            return

        if str(referral.get("home_assessment_done") or "").strip().upper() != "Y":
            ev = has_stage("HOME_ASSESSMENT_SCHEDULED")
            at = _parse_iso_datetime(ev.get("at")) if ev else None
            if at and (datetime.utcnow() - at).total_seconds() >= AUTOPILOT_HOME_ASSESSMENT_DELAY_SEC:
                _record_journey_event(rid, "HOME_ASSESSMENT_COMPLETED", source="autopilot")

        # Auto schedule if ready
        if str(referral.get("schedule_status") or "").strip().upper() == "NOT_SCHEDULED" and insurance_ok:
            if not _db_ready():
                # file mode caregiver pick + apply scheduling override
                caregivers = _load_caregivers_csv()
                overrides_sched = _load_scheduling_overrides()
                assignments = {
                    rrid: {
                        "referral_id": rrid,
                        "caregiver_id": o.get("assigned_caregiver_id"),
                        "schedule_status": o.get("schedule_status"),
                        "scheduled_date": o.get("scheduled_date"),
                    }
                    for rrid, o in overrides_sched.items()
                    if isinstance(o, dict)
                }
                all_refs = _load_referrals_csv()
                caregiver_id = _select_available_caregiver(referral, caregivers, assignments, all_refs)
                if caregiver_id:
                    overrides_sched[rid] = {
                        "schedule_status": "SCHEDULED",
                        "scheduled_date": date.today().isoformat(),
                        "assigned_caregiver_id": caregiver_id,
                        "updated_at": datetime.utcnow().isoformat() + "Z",
                    }
                    _save_scheduling_overrides(overrides_sched)
                    _record_journey_event(rid, "SCHEDULED", source="autopilot", note=f"Auto-scheduled with {caregiver_id}")

        # After scheduled, progress to billing and completion with delays
        overrides = _load_journey_overrides()
        entry = overrides.get(rid) if isinstance(overrides, dict) else None
        entry = entry if isinstance(entry, dict) else {"events": []}
        events = entry.get("events") if isinstance(entry.get("events"), list) else []
        sched_ev = None
        for ev in events:
            if isinstance(ev, dict) and str(ev.get("stage") or "").strip().upper() == "SCHEDULED":
                sched_ev = ev
                break
        if sched_ev and str(referral.get("schedule_status") or "").strip().upper() == "SCHEDULED":
            at = _parse_iso_datetime(sched_ev.get("at"))
            if at and (datetime.utcnow() - at).total_seconds() >= AUTOPILOT_READY_TO_BILL_DELAY_SEC:
                _record_journey_event(rid, "READY_TO_BILL", source="autopilot")
            rb_ev = None
            for ev in events:
                if isinstance(ev, dict) and str(ev.get("stage") or "").strip().upper() == "READY_TO_BILL":
                    rb_ev = ev
                    break
            if rb_ev:
                rb_at = _parse_iso_datetime(rb_ev.get("at"))
                if rb_at and (datetime.utcnow() - rb_at).total_seconds() >= AUTOPILOT_COMPLETE_DELAY_SEC:
                    _record_journey_event(rid, "SERVICE_COMPLETED", source="autopilot")
    except Exception:
        return


def _autopilot_tick_all() -> None:
    """Best-effort autopilot tick for runtime referrals (file mode)."""
    try:
        if not AUTOPILOT_ENABLED:
            return
        if _db_ready():
            return
        runtime = _load_runtime_referrals()
        if not runtime:
            return
        for r in runtime:
            _autopilot_tick_for_referral(r)
        # Reload and save with applied overrides to keep state consistent
        updated = _load_runtime_referrals()
        _save_runtime_referrals(updated)
    except Exception:
        return


def _load_compliance_docs() -> list[dict]:
    try:
        if not COMPLIANCE_DOCS_PATH.exists():
            return []
        with open(COMPLIANCE_DOCS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_compliance_docs(docs: list[dict]) -> None:
    COMPLIANCE_DOCS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(COMPLIANCE_DOCS_PATH, "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2, ensure_ascii=False)


def _classify_document_text(text: str) -> dict:
    """Heuristic classifier for arbitrary uploaded PDFs.

    Returns: {type: 'referral'|'compliance'|'other', confidence: 0..1, reasons: [..]}
    """
    t = (text or "").lower()
    t = " ".join(t.split())

    referral_kw = [
        "referral",
        "referring",
        "patient",
        "dob",
        "date of birth",
        "payer",
        "authorization",
        "auth required",
        "plan type",
        "diagnosis",
        "home health",
        "assessment",
        "intake",
        "start of care",
    ]
    compliance_kw = [
        "compliance",
        "policy",
        "procedure",
        "guideline",
        "regulation",
        "cms",
        "hipaa",
        "privacy",
        "security rule",
        "oig",
        "fraud",
        "abuse",
        "audit",
        "billing compliance",
        "documentation requirements",
    ]

    referral_hits = [kw for kw in referral_kw if kw in t]
    compliance_hits = [kw for kw in compliance_kw if kw in t]

    reasons: list[str] = []
    score_ref = len(referral_hits)
    score_comp = len(compliance_hits)

    if "referral" in t:
        score_ref += 3
    if "compliance" in t or "guideline" in t or "policy" in t:
        score_comp += 3

    if referral_hits:
        reasons.append(f"referral_keywords={referral_hits[:6]}")
    if compliance_hits:
        reasons.append(f"compliance_keywords={compliance_hits[:6]}")

    if score_ref == 0 and score_comp == 0:
        return {"type": "other", "confidence": 0.2, "reasons": ["no_keywords_detected"]}

    if score_comp >= max(3, score_ref + 1):
        conf = min(0.95, 0.55 + 0.08 * score_comp)
        return {"type": "compliance", "confidence": conf, "reasons": reasons or ["compliance_lean"]}
    if score_ref >= max(3, score_comp + 1):
        conf = min(0.95, 0.55 + 0.08 * score_ref)
        return {"type": "referral", "confidence": conf, "reasons": reasons or ["referral_lean"]}

    # Ambiguous: prefer compliance when any compliance keyword exists
    if score_comp > 0:
        return {"type": "compliance", "confidence": 0.55, "reasons": reasons + ["ambiguous_prefer_compliance"]}
    return {"type": "other", "confidence": 0.5, "reasons": reasons + ["ambiguous"]}

# Mount static files (CSS)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

def _csv_to_html_table(csv_path: Path, title: str) -> str:
        try:
                import csv
                if not csv_path.exists():
                        return f"<h2>{title}</h2><p>File not found: {csv_path}</p>"
                rows = []
                with open(csv_path, "r", encoding="utf-8") as f:
                        reader = csv.reader(f)
                        for row in reader:
                                rows.append(row)
                if not rows:
                        return f"<h2>{title}</h2><p>No data available.</p>"
                header = rows[0]
                body = rows[1:]
                th = "".join([f"<th>{h}</th>" for h in header])
                trs = "\n".join(["<tr>" + "".join([f"<td>{c}</td>" for c in r]) + "</tr>" for r in body])
                return f"""
                <h2>{title}</h2>
                <div class='table-container'>
                  <table class='data-table'>
                      <thead><tr>{th}</tr></thead>
                      <tbody>
                          {trs}
                      </tbody>
                  </table>
                </div>
                """
        except Exception as e:
                return f"<h2>{title}</h2><p>Error rendering table: {e}</p>"


def _parse_csv_dicts(csv_path: Path) -> list[dict]:
    try:
        if not csv_path.exists():
            return []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception:
        return []


def _safe_float(x: str) -> float:
    try:
        return float(str(x).strip())
    except Exception:
        return 0.0


_REFERRAL_INT_FIELDS = {
    "auth_units_total",
    "auth_units_remaining",
    "contact_attempts",
    "units_scheduled_next_7d",
    "units_delivered_to_date",
    "patient_age",
}

_CAREGIVER_INT_FIELDS = {"age"}


def _coerce_int_fields(row: dict, int_fields: set[str]) -> dict:
    for field in int_fields:
        if field in row:
            row[field] = _safe_int(row.get(field))
    return row


def _load_referrals_csv() -> list[dict]:
    rows = _parse_csv_dicts(REFERRALS_CSV)
    coerced = [_coerce_int_fields(r, _REFERRAL_INT_FIELDS) for r in rows]
    base = [_apply_journey_overrides(_apply_scheduling_overrides(r)) for r in coerced]
    runtime = _load_runtime_referrals()
    merged = runtime + base
    return merged


def _load_runtime_referrals() -> list[dict]:
    try:
        if not REFERRALS_RUNTIME_PATH.exists():
            return []
        with open(REFERRALS_RUNTIME_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        cleaned = []
        for row in data:
            if isinstance(row, dict):
                cleaned.append(_apply_journey_overrides(_apply_scheduling_overrides(_coerce_int_fields(row, _REFERRAL_INT_FIELDS))))
        return cleaned
    except Exception:
        return []


def _save_runtime_referrals(rows: list[dict]) -> None:
    REFERRALS_RUNTIME_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REFERRALS_RUNTIME_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)


def _next_referral_id(existing_ids: list[str]) -> str:
    max_n = 1000
    for rid in existing_ids:
        try:
            s = str(rid)
            if s.startswith("REF-"):
                n = int(s.split("REF-")[-1])
                max_n = max(max_n, n)
        except Exception:
            continue
    return f"REF-{max_n + 1}"


def _kv_lines_from_text(text: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for line in (text or "").splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()
        if not key or not val:
            continue
        if len(key) >= 80:
            continue
        pairs.append((key, val))
    return pairs


def _normalize_extracted_kv_to_referral_fields(pairs: list[tuple[str, str]]) -> dict:
    """Map LandingAI extracted KV-ish lines to our referral schema fields."""

    def norm_key(k: str) -> Optional[str]:
        kl = k.strip().lower()
        mapping = {
            "referral id": "referral_id",
            "payer": "payer",
            "payer name": "payer",
            "plan type": "plan_type",
            "authorization status": "auth_status",
            "authorization required": "auth_required",
            "authorization start date": "auth_start_date",
            "authorization end date": "auth_end_date",
            "authorized units": "auth_units_total",
            "units delivered": "units_delivered_to_date",
            "units used": "units_delivered_to_date",
            "unit type": "unit_type",
            "city": "patient_city",
            "service category": "service_type",
        }
        return mapping.get(kl)

    out: dict = {}
    for k, v in pairs:
        nk = norm_key(k)
        if not nk:
            continue
        if nk in out and out.get(nk):
            continue
        out[nk] = v

    # Normalize auth_required to Y/N when possible
    if "auth_required" in out:
        s = str(out.get("auth_required") or "").strip().lower()
        if s in ("yes", "y", "true", "1"):
            out["auth_required"] = "Y"
        elif s in ("no", "n", "false", "0"):
            out["auth_required"] = "N"

    # Normalize auth_status common variants
    if "auth_status" in out:
        s = str(out.get("auth_status") or "").strip().upper()
        # Keep only the statuses our dataset tends to use
        if "APPROV" in s:
            out["auth_status"] = "APPROVED"
        elif "DEN" in s:
            out["auth_status"] = "DENIED"
        elif "EXPIR" in s:
            out["auth_status"] = "EXPIRED"
        else:
            out["auth_status"] = s

    # Dates: keep ISO yyyy-mm-dd if it looks like a date
    for dk in ("auth_start_date", "auth_end_date"):
        if dk in out:
            d = _safe_date(out.get(dk))
            out[dk] = d.isoformat() if d else str(out.get(dk))

    # Int-ish fields
    for ik in ("auth_units_total", "units_delivered_to_date"):
        if ik in out:
            out[ik] = _safe_int(out.get(ik))

    return out


@app.post("/api/v1/intake/from-pdf")
async def intake_from_pdf(files: List[UploadFile] = File(...)):
    """Upload PDFs, parse via LandingAI, then classify:

    - referral: normalize fields and create a new referral (enters the ops + scheduler flow)
    - compliance: store as a guardrail document (does NOT create a referral)
    - other: keep a record in response but do nothing
    """
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files uploaded")
        if not landingai_service:
            raise HTTPException(
                status_code=500,
                detail="LandingAI is not configured. Set LANDING_AI_API_KEY in backend/.env (repo root .env) and restart backend.",
            )

        created = []
        compliance_saved = []
        ignored = []
        errors = []

        # Baseline dataset for consistent fields
        base_rows = _parse_csv_dicts(REFERRALS_CSV)
        if not base_rows:
            raise HTTPException(status_code=500, detail="Synthetic referrals CSV is empty")

        runtime_rows = _load_runtime_referrals()
        existing_ids = [r.get("referral_id") for r in base_rows if r.get("referral_id")]
        existing_ids += [r.get("referral_id") for r in runtime_rows if r.get("referral_id")]
        existing_ids = [str(x) for x in existing_ids if x]

        compliance_docs = _load_compliance_docs()

        for f in files:
            try:
                file_bytes = await f.read()
                if not file_bytes:
                    raise ValueError("Empty file")

                parse_result = await landingai_service.process_document(
                    file_bytes=file_bytes,
                    document_type="referral_packet",
                )
                if not parse_result.get("success"):
                    raise ValueError(parse_result.get("message") or "LandingAI parse failed")

                extracted_text = (parse_result.get("extracted_data") or {}).get("text") or ""
                classification = _classify_document_text(extracted_text)

                doc_type = classification.get("type")
                if doc_type == "compliance":
                    # Store guardrail doc for the rest of the system
                    doc_id = f"COMP-{int(datetime.utcnow().timestamp())}-{random.randint(100, 999)}"
                    excerpt = (extracted_text or "").strip().replace("\n", " ")[:1200]
                    compliance_docs.insert(
                        0,
                        {
                            "compliance_id": doc_id,
                            "source_filename": f.filename,
                            "created_at": datetime.utcnow().isoformat() + "Z",
                            "classification": classification,
                            "excerpt": excerpt,
                            "landingai": {
                                "processing_time": parse_result.get("processing_time"),
                                "metadata": parse_result.get("metadata"),
                            },
                        },
                    )
                    compliance_saved.append(
                        {
                            "compliance_id": doc_id,
                            "source_filename": f.filename,
                            "classification": classification,
                        }
                    )
                    continue

                if doc_type != "referral":
                    ignored.append(
                        {
                            "source_filename": f.filename,
                            "classification": classification,
                        }
                    )
                    continue

                pairs = _kv_lines_from_text(extracted_text)
                mapped = _normalize_extracted_kv_to_referral_fields(pairs)

                template = dict(random.choice(base_rows))

                new_id = mapped.get("referral_id")
                if new_id:
                    new_id = str(new_id).strip()
                if not new_id or new_id in existing_ids:
                    new_id = _next_referral_id(existing_ids)

                existing_ids.append(new_id)

                today = date.today()
                new_row = template
                new_row["referral_id"] = new_id
                new_row["referral_received_date"] = today.isoformat()
                new_row["schedule_status"] = "NOT_SCHEDULED"
                new_row["scheduled_date"] = ""
                new_row["service_complete"] = "N"
                new_row["insurance_active"] = "Y"
                new_row["contact_attempts"] = 0
                new_row["docs_complete"] = "N"
                new_row["home_assessment_done"] = "N"
                new_row["ready_to_bill"] = "N"
                new_row["referral_source"] = "LandingAI PDF"
                new_row["agent_next_action"] = "Review and schedule"
                new_row["agent_rationale"] = f"Ingested from PDF via LandingAI: {f.filename}"

                # Apply extracted mappings
                for k, v in mapped.items():
                    if k == "referral_id":
                        continue
                    # Map extracted schema keys to our dataset keys
                    if k == "auth_required":
                        new_row["auth_required"] = v
                    elif k == "auth_status":
                        new_row["auth_status"] = v
                    elif k == "auth_start_date":
                        new_row["auth_start_date"] = v
                    elif k == "auth_end_date":
                        new_row["auth_end_date"] = v
                    elif k == "auth_units_total":
                        new_row["auth_units_total"] = v
                    elif k == "units_delivered_to_date":
                        new_row["units_delivered_to_date"] = v
                    elif k in ("payer", "plan_type", "unit_type", "patient_city", "service_type"):
                        new_row[k] = v

                # Segment heuristic for demo
                urg = str(new_row.get("urgency") or "").strip().lower()
                if urg == "urgent":
                    new_row["agent_segment"] = "RED"
                elif not new_row.get("agent_segment"):
                    new_row["agent_segment"] = "GREEN"

                new_row = _coerce_int_fields(new_row, _REFERRAL_INT_FIELDS)

                if _db_ready():
                    cols = [
                        'referral_id', 'use_case', 'service_type', 'referral_source',
                        'urgency', 'referral_received_date', 'first_outreach_date',
                        'last_activity_date', 'insurance_active', 'payer', 'plan_type',
                        'auth_required', 'auth_status', 'auth_start_date', 'auth_end_date',
                        'auth_units_total', 'auth_units_remaining', 'unit_type',
                        'docs_complete', 'home_assessment_done', 'patient_responsive',
                        'contact_attempts', 'schedule_status', 'scheduled_date',
                        'units_scheduled_next_7d', 'units_delivered_to_date',
                        'service_complete', 'evv_or_visit_note_exists', 'ready_to_bill',
                        'claim_status', 'denial_reason', 'payment_amount', 'patient_dob',
                        'patient_age', 'patient_gender', 'patient_address', 'patient_city',
                        'patient_zip', 'agent_segment', 'agent_next_action', 'agent_rationale'
                    ]
                    values = [new_row.get(c) for c in cols]
                    placeholders = ",".join(["%s"] * len(cols))
                    insert_sql = f"INSERT INTO referrals ({','.join(cols)}) VALUES ({placeholders})"
                    res = db_service.query(insert_sql, tuple(values))
                    if not res.get('success'):
                        raise ValueError(res.get('message'))
                else:
                    runtime_rows.insert(0, new_row)

                created.append({
                    "referral": new_row,
                    "source_filename": f.filename,
                    "classification": classification,
                    "landingai": {
                        "processing_time": parse_result.get("processing_time"),
                        "metadata": parse_result.get("metadata"),
                    },
                })

            except Exception as e:
                errors.append({"filename": getattr(f, "filename", "unknown"), "error": str(e)})

        if compliance_docs:
            _save_compliance_docs(compliance_docs[:200])

        if not _db_ready():
            _save_runtime_referrals(runtime_rows)

        # Keep the system agentic: tick autopilot so stages/scheduling progress automatically.
        _autopilot_tick_all()

        # Refresh created referrals with latest overrides for accurate UI updates.
        for item in created:
            rr = item.get("referral")
            if isinstance(rr, dict):
                item["referral"] = _apply_journey_overrides(_apply_scheduling_overrides(rr))

        return {
            "success": True,
            "mode": "db" if _db_ready() else "file",
            "created": created,
            "compliance_saved": compliance_saved,
            "ignored": ignored,
            "errors": errors,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed PDF intake: {str(e)}")


@app.post("/api/v1/intake/simulate")
async def simulate_referral_intake(
    urgency: Optional[str] = None,
    patient_city: Optional[str] = None,
    payer: Optional[str] = None,
    service_type: Optional[str] = None,
):
    """Simulate a new referral arriving (demo intake button).

    Uses synthetic dataset fields as the source of truth.
    - If DB is available: inserts into `referrals`.
    - Else: appends to `data/referrals_runtime.json`.
    """
    try:
        today = date.today()

        # Pick a template row from the synthetic CSV so fields look realistic
        base_rows = _parse_csv_dicts(REFERRALS_CSV)
        if not base_rows:
            raise HTTPException(status_code=500, detail="Synthetic referrals CSV is empty or not found")
        template = random.choice(base_rows)

        # Collect existing IDs (CSV + runtime + DB)
        existing_ids = [r.get("referral_id") for r in base_rows if r.get("referral_id")]
        runtime_rows = _load_runtime_referrals()
        existing_ids += [r.get("referral_id") for r in runtime_rows if r.get("referral_id")]
        
        # Also check DB for existing IDs
        if _db_ready():
            db_result = db_service.query("SELECT referral_id FROM referrals")
            if db_result.get("success") and db_result.get("data"):
                existing_ids += [r.get("referral_id") for r in db_result["data"] if r.get("referral_id")]
        
        new_id = _next_referral_id([str(x) for x in existing_ids if x])

        # Random values for realistic demo
        cities = ["San Francisco", "Oakland", "Berkeley", "San Jose", "Fremont", "Dublin", "San Leandro"]
        payers = ["Medicare", "Medi-Cal", "BlueCross", "Aetna", "Cigna", "United", "Anthem"]
        service_types = ["PersonalCare", "HomeHealthNursing", "HomeHealthPT", "BehavioralHealth", "ECM", "CS_NutritionSupport"]
        urgencies = ["Routine", "Urgent"]
        plan_types = ["HMO", "PPO", "FFS", "Medicaid", "Commercial"]

        new_row = dict(template)
        new_row["referral_id"] = new_id
        new_row["use_case"] = "HOME_CARE"
        new_row["service_type"] = service_type or random.choice(service_types)
        new_row["referral_source"] = random.choice(["PCP", "Hospital", "County", "Self", "Payer"])
        new_row["urgency"] = urgency or random.choice(urgencies)
        new_row["referral_received_date"] = today.isoformat()
        new_row["first_outreach_date"] = ""
        new_row["last_activity_date"] = today.isoformat()
        new_row["insurance_active"] = "Y"
        new_row["payer"] = payer or random.choice(payers)
        new_row["plan_type"] = random.choice(plan_types)
        
        # Initial stage: auth pending or not required
        needs_auth = random.choice([True, False])
        new_row["auth_required"] = "Y" if needs_auth else "N"
        new_row["auth_status"] = "PENDING" if needs_auth else "NOT_REQUIRED"
        new_row["auth_start_date"] = today.isoformat() if needs_auth else ""
        new_row["auth_end_date"] = (today + timedelta(days=random.randint(30, 90))).isoformat() if needs_auth else ""
        new_row["auth_units_total"] = random.randint(10, 80) if needs_auth else random.randint(20, 60)
        new_row["auth_units_remaining"] = new_row["auth_units_total"]
        new_row["unit_type"] = random.choice(["HOURS", "VISITS"])

        # Reset journey state so the agentic timeline is visible
        new_row["docs_complete"] = "N"
        new_row["home_assessment_done"] = "N"
        new_row["patient_responsive"] = random.choice(["HIGH", "MED", "LOW"])
        new_row["contact_attempts"] = 0
        new_row["schedule_status"] = "NOT_SCHEDULED"
        new_row["scheduled_date"] = ""
        new_row["units_scheduled_next_7d"] = 0
        new_row["units_delivered_to_date"] = 0
        new_row["service_complete"] = "N"
        new_row["evv_or_visit_note_exists"] = "N"
        new_row["ready_to_bill"] = "N"
        new_row["claim_status"] = "NOT_SUBMITTED"
        new_row["denial_reason"] = ""
        new_row["payment_amount"] = 0

        # Patient info from template or random
        new_row["patient_city"] = patient_city or random.choice(cities)
        
        # Agent segment based on urgency and auth status
        urg = str(new_row.get("urgency") or "").strip().lower()
        auth_stat = str(new_row.get("auth_status") or "").strip().upper()
        if urg == "urgent":
            new_row["agent_segment"] = "RED" if auth_stat == "PENDING" else "ORANGE"
        elif auth_stat == "PENDING":
            new_row["agent_segment"] = "YELLOW"
        else:
            new_row["agent_segment"] = "GREEN"
        
        # Set appropriate next action based on state
        if auth_stat == "PENDING":
            new_row["agent_next_action"] = "FOLLOW_UP_AUTH"
            new_row["agent_rationale"] = "New intake; authorization pending - follow up with payer."
        else:
            new_row["agent_next_action"] = "REQUEST_DOCS"
            new_row["agent_rationale"] = "New intake; gather required documents to proceed."

        # Coerce numeric fields
        new_row = _coerce_int_fields(new_row, _REFERRAL_INT_FIELDS)

        if _db_ready():
            # Insert only the columns present in schema (ignore extras)
            cols = [
                'referral_id', 'use_case', 'service_type', 'referral_source',
                'urgency', 'referral_received_date', 'first_outreach_date',
                'last_activity_date', 'insurance_active', 'payer', 'plan_type',
                'auth_required', 'auth_status', 'auth_start_date', 'auth_end_date',
                'auth_units_total', 'auth_units_remaining', 'unit_type',
                'docs_complete', 'home_assessment_done', 'patient_responsive',
                'contact_attempts', 'schedule_status', 'scheduled_date',
                'units_scheduled_next_7d', 'units_delivered_to_date',
                'service_complete', 'evv_or_visit_note_exists', 'ready_to_bill',
                'claim_status', 'denial_reason', 'payment_amount', 'patient_dob',
                'patient_age', 'patient_gender', 'patient_address', 'patient_city',
                'patient_zip', 'agent_segment', 'agent_next_action', 'agent_rationale'
            ]
            # Convert empty strings to None for date columns (PostgreSQL requires NULL, not '')
            date_cols = {'referral_received_date', 'first_outreach_date', 'last_activity_date',
                         'auth_start_date', 'auth_end_date', 'scheduled_date', 'patient_dob'}
            values = []
            for c in cols:
                val = new_row.get(c)
                # Convert empty string to None for date fields
                if c in date_cols and val == '':
                    val = None
                values.append(val)
            placeholders = ",".join(["%s"] * len(cols))
            insert_sql = f"INSERT INTO referrals ({','.join(cols)}) VALUES ({placeholders})"
            res = db_service.query(insert_sql, tuple(values))
            if not res.get('success'):
                raise HTTPException(status_code=500, detail=res.get('message'))

            # DB mode: autopilot currently runs only in file mode.
            return {"success": True, "mode": "db", "referral": new_row}

        # File/demo mode
        runtime_rows.insert(0, new_row)
        _save_runtime_referrals(runtime_rows)

        # Keep agentic behavior consistent: tick autopilot after intake.
        _autopilot_tick_all()

        # Return the view with latest overrides applied.
        new_row = _apply_journey_overrides(_apply_scheduling_overrides(new_row))
        return {"success": True, "mode": "file", "referral": new_row}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to simulate intake: {str(e)}")


@app.get("/api/v1/compliance/docs")
async def list_compliance_docs(limit: int = Query(50, ge=1, le=200)):
    try:
        docs = _load_compliance_docs()
        return {
            "success": True,
            "count": len(docs),
            "docs": docs[:limit],
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load compliance docs: {str(e)}")


@app.get("/api/v1/compliance/guardrails")
async def get_compliance_guardrails():
    """Return a lightweight guardrails payload for agents/UI."""
    try:
        docs = _load_compliance_docs()
        items = []
        for d in docs[:25]:
            items.append(
                {
                    "compliance_id": d.get("compliance_id"),
                    "source_filename": d.get("source_filename"),
                    "created_at": d.get("created_at"),
                    "excerpt": d.get("excerpt"),
                    "classification": d.get("classification"),
                }
            )
        return {
            "success": True,
            "guardrails": items,
            "count": len(docs),
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build guardrails: {str(e)}")


def _journey_default_timeline(referral: dict) -> list[dict]:
    """Derive a baseline journey from referral fields."""
    rid = referral.get("referral_id")
    items = [
        {
            "stage": "INTAKE_RECEIVED",
            "at": referral.get("referral_received_date") or "",
            "source": "dataset",
        }
    ]
    if str(referral.get("docs_complete") or "").strip().upper() == "Y":
        items.append({"stage": "DOCS_COMPLETED", "at": referral.get("last_activity_date") or "", "source": "dataset"})
    if str(referral.get("home_assessment_done") or "").strip().upper() == "Y":
        items.append({"stage": "HOME_ASSESSMENT_COMPLETED", "at": referral.get("last_activity_date") or "", "source": "dataset"})
    if str(referral.get("schedule_status") or "").strip().upper() == "SCHEDULED":
        items.append({"stage": "SCHEDULED", "at": referral.get("scheduled_date") or "", "source": "dataset"})
    if str(referral.get("ready_to_bill") or "").strip().upper() == "Y":
        items.append({"stage": "READY_TO_BILL", "at": referral.get("last_activity_date") or "", "source": "dataset"})
    if str(referral.get("service_complete") or "").strip().upper() == "Y":
        items.append({"stage": "SERVICE_COMPLETED", "at": referral.get("last_activity_date") or "", "source": "dataset"})
    return items


@app.get("/api/v1/referrals/{referral_id}/journey")
async def get_referral_journey(referral_id: str):
    try:
        rid = str(referral_id or "").strip()
        if not rid:
            raise HTTPException(status_code=400, detail="referral_id is required")

        # Find referral
        if _db_ready():
            r = db_service.query("SELECT * FROM referrals WHERE referral_id = %s", (rid,))
            if not r.get("success"):
                raise HTTPException(status_code=500, detail=r.get("message"))
            rows = r.get("data") or []
            if not rows:
                raise HTTPException(status_code=404, detail="Referral not found")
            referral = rows[0]
        else:
            rows = _load_referrals_csv()
            referral = next((x for x in rows if str(x.get("referral_id") or "").strip() == rid), None)
            if not referral:
                raise HTTPException(status_code=404, detail="Referral not found")

        overrides = _load_journey_overrides()
        entry = overrides.get(rid) if isinstance(overrides, dict) else None
        entry = entry if isinstance(entry, dict) else {"events": []}
        events = entry.get("events") if isinstance(entry.get("events"), list) else []

        timeline = _journey_default_timeline(referral)
        for ev in events:
            if isinstance(ev, dict) and ev.get("stage"):
                timeline.append(ev)

        current_stage = entry.get("current_stage")
        if not current_stage:
            # Heuristic current stage
            current_stage = (timeline[-1].get("stage") if timeline else "INTAKE_RECEIVED")

        return {
            "success": True,
            "referral_id": rid,
            "current_stage": current_stage,
            "timeline": timeline,
            "updated_at": entry.get("updated_at"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load journey: {str(e)}")


@app.post("/api/v1/referrals/{referral_id}/journey/advance")
async def advance_referral_journey(referral_id: str, stage: str, note: Optional[str] = None):
    """Advance a referral through the demo journey.

    Persists to journey_overrides.json (file mode) and updates referral fields (file/DB) so ops KPIs and scheduler react.
    """
    try:
        rid = str(referral_id or "").strip()
        st = str(stage or "").strip().upper()
        if not rid:
            raise HTTPException(status_code=400, detail="referral_id is required")
        if not st:
            raise HTTPException(status_code=400, detail="stage is required")

        now = datetime.utcnow().isoformat() + "Z"
        ev = {"stage": st, "at": now, "source": "ui", "note": (note or "").strip()}

        overrides = _load_journey_overrides()
        entry = overrides.get(rid)
        if not isinstance(entry, dict):
            entry = {"events": []}
        events = entry.get("events")
        if not isinstance(events, list):
            events = []
        events.append(ev)
        entry["events"] = events
        entry["current_stage"] = st
        entry["updated_at"] = now
        overrides[rid] = entry
        _save_journey_overrides(overrides)

        # Apply side effects to referral row so the rest of the system updates
        if _db_ready():
            updates: dict[str, object] = {
                "updated_at": datetime.utcnow(),
            }
            
            # Try to update journey_stage if column exists (migration may not have run)
            try:
                journey_res = db_service.query(
                    "UPDATE referrals SET journey_stage = %s, journey_updated_at = %s WHERE referral_id = %s",
                    (st, datetime.utcnow(), rid)
                )
                # If it fails silently, that's OK - column may not exist
            except Exception:
                pass  # Column doesn't exist yet
            
            if st == "DOCS_COMPLETED":
                updates.update({"docs_complete": "Y"})
            elif st == "HOME_ASSESSMENT_COMPLETED":
                updates.update({"home_assessment_done": "Y"})
            elif st == "READY_TO_BILL":
                updates.update({"ready_to_bill": "Y"})
            elif st == "SERVICE_COMPLETED":
                updates.update({"service_complete": "Y", "schedule_status": "COMPLETED"})

            if updates:
                set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
                params = list(updates.values()) + [rid]
                res = db_service.query(f"UPDATE referrals SET {set_clause} WHERE referral_id = %s", tuple(params))
                if not res.get("success"):
                    raise HTTPException(status_code=500, detail=res.get("message"))

        return {"success": True, "referral_id": rid, "current_stage": st, "event": ev}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to advance journey: {str(e)}")


def _load_caregivers_csv() -> list[dict]:
    rows = _parse_csv_dicts(CAREGIVERS_CSV)
    return [_coerce_int_fields(r, _CAREGIVER_INT_FIELDS) for r in rows]


def _db_ready() -> bool:
    global db_service
    if not db_service:
        return False
    if getattr(db_service, "connection", None) is not None and getattr(db_service, "cursor", None) is not None:
        return True
    try:
        result = db_service.connect()
        return bool(result.get("success"))
    except Exception:
        return False


def _render_cards(cards: list[tuple[str, str]]) -> str:
    items = "".join([f"<div class='card'><h3>{title}</h3><div class='stat'>{value}</div></div>" for title, value in cards])
    return f"<div class='card-grid'>{items}</div>"


def _format_seconds_avg(values: list[float]) -> str:
    if not values:
        return "—"
    avg = sum(values) / len(values)
    return f"{avg:.2f}s"


def _safe_int(x: str) -> int:
    try:
        return int(str(x).strip())
    except Exception:
        return 0


def _summarize_outcomes(rows: list[dict]) -> dict:
    d = {
        "referral_received": 0,
        "intake_complete": 0,
        "assessment_complete": 0,
        "eligibility_verified": 0,
        "auth_required": 0,
        "auth_approved": 0,
        "ready_to_schedule": 0,
        "outcomes_count": len(rows),
    }
    caregivers = {}
    for r in rows:
        def is_true(v):
            s = str(v or "").strip().lower()
            return s in ("true", "yes", "1")
        if is_true(r.get("referral_received")): d["referral_received"] += 1
        if is_true(r.get("intake_complete")): d["intake_complete"] += 1
        if is_true(r.get("assessment_complete")): d["assessment_complete"] += 1
        if is_true(r.get("eligibility_verified")): d["eligibility_verified"] += 1
        if is_true(r.get("auth_required")): d["auth_required"] += 1
        if is_true(r.get("auth_approved")): d["auth_approved"] += 1
        if is_true(r.get("ready_to_schedule")): d["ready_to_schedule"] += 1
        cg = (r.get("matched_caregiver_id") or "").strip()
        if cg:
            caregivers[cg] = caregivers.get(cg, 0) + 1
    d["caregivers_unique"] = len(caregivers)
    d["caregivers_multi_assign"] = sum(1 for k,v in caregivers.items() if v >= 2)
    d["caregivers_clients_avg"] = (sum(caregivers.values())/len(caregivers)) if caregivers else 0.0
    return d


def _build_dashboard_metrics() -> dict:
    norm_rows = _parse_csv_dicts(DOC_EXTRACT_DIR / "normalized_summary.csv")
    indiv_rows = _parse_csv_dicts(DOC_EXTRACT_DIR / "individual" / "summary_individual.csv")
    outcomes_rows = _parse_csv_dicts(DOC_EXTRACT_DIR / "pipeline_outcomes.csv")
    referrals_rows = _parse_csv_dicts(REPO_ROOT / "data" / "referrals_synthetic.csv")
    caregivers_rows = _parse_csv_dicts(REPO_ROOT / "data" / "caregivers_synthetic.csv")
    auth_required_yes = sum(
        1 for r in norm_rows if str(r.get("authorization_required", "")).strip().lower() in ("yes", "true")
    )
    auth_approved = sum(
        1 for r in norm_rows if str(r.get("authorization_status", "")).strip().lower() == "approved"
    )
    ready_to_bill = sum(1 for r in norm_rows if str(r.get("ready_to_bill", "")).strip().lower() in ("yes", "true"))
    units_authorized = sum(_safe_int(r.get("authorized_units", 0)) for r in norm_rows)
    units_delivered = sum(_safe_int(r.get("units_delivered", 0)) for r in norm_rows)

    total_docs = len(indiv_rows)
    success_docs = sum(1 for r in indiv_rows if str(r.get("success", "")).strip().lower() in ("true", "yes"))
    success_rate = f"{(success_docs / total_docs * 100):.1f}%" if total_docs else "—"
    proc_times = []
    for r in indiv_rows:
        try:
            proc_times.append(float(r.get("processing_time", 0)))
        except Exception:
            pass
    avg_proc = _format_seconds_avg(proc_times)

    outcome_stats = _summarize_outcomes(outcomes_rows)
    ready = outcome_stats["ready_to_schedule"]
    matched = outcome_stats["caregivers_unique"]

    cards = [
        ("Referrals (CSV)", str(len(referrals_rows))),
        ("Outcomes Rows", str(outcome_stats["outcomes_count"])),
        ("Caregivers (CSV)", str(len(caregivers_rows))),
        ("Auth Required", str(auth_required_yes)),
        ("Auth Approved", str(auth_approved)),
        ("Ready to Bill", str(ready_to_bill)),
        ("Units Authorized", str(units_authorized)),
        ("Units Delivered", str(units_delivered)),
        ("Docs Processed", str(total_docs)),
        ("Success Rate", success_rate),
        ("Avg Proc Time", avg_proc),
        ("Ready to Schedule", str(ready)),
        ("Caregivers Matched (unique)", str(matched)),
        ("Caregivers Multi-Assign", str(outcome_stats["caregivers_multi_assign"])),
        ("Avg Clients/Caregiver", f"{outcome_stats['caregivers_clients_avg']:.2f}"),
    ]

    funnel = [
        ("Referral Received", outcome_stats["referral_received"]),
        ("Intake Complete", outcome_stats["intake_complete"]),
        ("Assessment Complete", outcome_stats["assessment_complete"]),
        ("Eligibility Verified", outcome_stats["eligibility_verified"]),
        ("Auth Required", outcome_stats["auth_required"]),
        ("Auth Approved", outcome_stats["auth_approved"]),
        ("Ready To Schedule", outcome_stats["ready_to_schedule"]),
    ]

    return {
        "cards": [{"title": title, "value": value} for title, value in cards],
        "funnel": [{"stage": stage, "count": count} for stage, count in funnel],
    }


@app.get("/ui/summary", response_class=HTMLResponse)
async def ui_summary():
    path = DOC_EXTRACT_DIR / "normalized_summary.csv"
    content = _csv_to_html_table(path, "Normalized Referral Summary")
    return f"""
    <html>
        <head>
            <title>HealthOps Summary</title>
            <link rel="stylesheet" href="/static/style.css">
            <meta name="viewport" content="width=device-width, initial-scale=1" />
        </head>
        <body>
            <header>
                <h1>HealthOps Document Parsing</h1>
                <nav>
                    <a href='/ui/summary'>Summary</a>
                    <a href='/ui/individual'>Per-Document Summary</a>
                    <a href='/ui/dashboard'>Dashboard</a>
                </nav>
            </header>
            <main>
                {content}
            </main>
        </body>
    </html>
    """


@app.get("/ui/individual", response_class=HTMLResponse)
async def ui_individual():
    path = DOC_EXTRACT_DIR / "individual" / "summary_individual.csv"
    content = _csv_to_html_table(path, "Per-Document Parsing Summary")
    return f"""
    <html>
        <head>
            <title>HealthOps Per-Document Summary</title>
            <link rel="stylesheet" href="/static/style.css">
            <meta name="viewport" content="width=device-width, initial-scale=1" />
        </head>
        <body>
            <header>
                <h1>HealthOps Document Parsing</h1>
                <nav>
                    <a href='/ui/summary'>Summary</a>
                    <a href='/ui/individual'>Per-Document Summary</a>
                    <a href='/ui/dashboard'>Dashboard</a>
                </nav>
            </header>
            <main>
                {content}
            </main>
        </body>
    </html>
    """


@app.get("/ui/dashboard", response_class=HTMLResponse)
async def ui_dashboard():
    metrics = _build_dashboard_metrics()
    cards_html = _render_cards([(item["title"], item["value"]) for item in metrics["cards"]])
    funnel_rows = "\n".join(
        [f"<tr><td>{item['stage']}</td><td>{item['count']}</td></tr>" for item in metrics["funnel"]]
    )

    return f"""
        <html>
                <head>
                        <title>HealthOps Dashboard</title>
                        <link rel=\"stylesheet\" href=\"/static/style.css\">
                        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
                </head>
                <body>
                        <header>
                                <h1>HealthOps Dashboard</h1>
                                <nav>
                                        <a href='/ui/summary'>Summary</a>
                                        <a href='/ui/individual'>Per-Document Summary</a>
                                        <a href='/ui/dashboard'>Dashboard</a>
                                </nav>
                        </header>
                        <main>
                            {cards_html}
                            <h2>Funnel</h2>
                            <div class='table-container'>
                                <table class='data-table'>
                                    <thead><tr>
                                        <th>Stage</th><th>Count</th>
                                    </tr></thead>
                                    <tbody>
                                        {funnel_rows}
                                    </tbody>
                                </table>
                            </div>
                        </main>
                </body>
        </html>
        """


@app.get("/ui/pipeline", response_class=HTMLResponse)
async def ui_pipeline():
    path = DOC_EXTRACT_DIR / "pipeline_outcomes.csv"
    content = _csv_to_html_table(path, "Pipeline Outcomes")
    return f"""
    <html>
        <head>
            <title>HealthOps Pipeline Outcomes</title>
            <link rel=\"stylesheet\" href=\"/static/style.css\">
            <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
        </head>
        <body>
            <header>
                <h1>HealthOps Pipeline Outcomes</h1>
                <nav>
                    <a href='/ui/summary'>Summary</a>
                    <a href='/ui/individual'>Per-Document Summary</a>
                    <a href='/ui/dashboard'>Dashboard</a>
                    <a href='/ui/pipeline'>Pipeline</a>
                </nav>
            </header>
            <main>
                {content}
            </main>
        </body>
    </html>
    """

@app.get("/ui/caregivers", response_class=HTMLResponse)
async def ui_caregivers():
        outcomes_rows = _parse_csv_dicts(DOC_EXTRACT_DIR / "pipeline_outcomes.csv")
        caregivers_rows = _parse_csv_dicts(REPO_ROOT / "data" / "caregivers_synthetic.csv")
        # Aggregate matches per caregiver
        counts: dict[str,int] = {}
        for r in outcomes_rows:
                cg = (r.get("matched_caregiver_id") or "").strip()
                rid = r.get("referral_id")
                if cg:
                        counts[cg] = counts.get(cg, 0) + 1
        # build rows
        idx = {c.get("caregiver_id"): c for c in caregivers_rows}
        table_rows = []
        for cg_id, cnt in sorted(counts.items(), key=lambda kv: kv[1], reverse=True):
                c = idx.get(cg_id) or {}
                table_rows.append([cg_id, c.get("city","—"), c.get("skills","—"), str(cnt)])
        # render table
        th = "".join([f"<th>{h}</th>" for h in ("Caregiver","City","Skills","Assigned Clients")])
        trs = "\n".join(["<tr>" + "".join([f"<td>{cell}</td>" for cell in row]) + "</tr>" for row in table_rows])
        content = f"""
            <div class='table-container'>
                <table class='data-table'>
                    <thead><tr>{th}</tr></thead>
                    <tbody>{trs}</tbody>
                </table>
            </div>
        """
        return f"""
        <html>
                <head>
                    <title>Caregivers Summary</title>
                    <link rel=\"stylesheet\" href=\"/static/style.css\">
                    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
                </head>
                <body>
                        <header>
                            <h1>Caregivers Summary</h1>
                            <nav>
                                    <a href='/ui/summary'>Summary</a>
                                    <a href='/ui/individual'>Per-Document Summary</a>
                                    <a href='/ui/dashboard'>Dashboard</a>
                                    <a href='/ui/pipeline'>Pipeline</a>
                                    <a href='/ui/referrals'>Referrals</a>
                                    <a href='/ui/caregivers'>Caregivers</a>
                            </nav>
                        </header>
                        <main>
                            {content}
                        </main>
                </body>
        </html>
        """


# --- Interactive Referrals UI + API ---
@app.get("/api/outcomes")
async def api_outcomes():
    outcomes_rows = _parse_csv_dicts(DOC_EXTRACT_DIR / "pipeline_outcomes.csv")
    referrals_rows = _parse_csv_dicts(REPO_ROOT / "data" / "referrals_synthetic.csv")
    # Build index by referral_id for quick join
    idx = {r.get("referral_id"): r for r in referrals_rows}
    joined = []
    for o in outcomes_rows:
        rid = o.get("referral_id")
        r = idx.get(rid) or {}
        joined.append({
            **o,
            "agent_segment": r.get("agent_segment"),
            "agent_next_action": r.get("agent_next_action"),
            "agent_rationale": r.get("agent_rationale"),
            "payer": r.get("payer"),
            "plan_type": r.get("plan_type"),
            "patient_city": r.get("patient_city"),
        })
    return {"data": joined}


@app.get("/ui/referrals", response_class=HTMLResponse)
async def ui_referrals():
    return """
        <html>
                <head>
                    <title>HealthOps Referrals</title>
                    <link rel=\"stylesheet\" href=\"/static/style.css\">
                    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
                </head>
                <body>
                        <header>
                            <h1>HealthOps Referrals</h1>
                            <nav>
                                    <a href='/ui/summary'>Summary</a>
                                    <a href='/ui/individual'>Per-Document Summary</a>
                                    <a href='/ui/dashboard'>Dashboard</a>
                                    <a href='/ui/pipeline'>Pipeline</a>
                                    <a href='/ui/referrals'>Referrals</a>
                            </nav>
                        </header>
                        <main>
                            <div id='app'>
                                <div class='filters'>
                                    <input id='search' placeholder='Search referral ID or city' />
                                    <select id='state'>
                                        <option value=''>All States</option>
                                        <option>REFERRAL_RECEIVED</option>
                                        <option>INTAKE_COMPLETE</option>
                                        <option>ASSESSMENT_COMPLETE</option>
                                        <option>ELIGIBILITY_VERIFIED</option>
                                        <option>AUTH_PENDING</option>
                                        <option>AUTH_APPROVED</option>
                                        <option>READY_TO_SCHEDULE</option>
                                    </select>
                                    <select id='segment'>
                                        <option value=''>All Segments</option>
                                        <option>GREEN</option>
                                        <option>ORANGE</option>
                                        <option>RED</option>
                                    </select>
                                </div>
                                <div id='table'></div>
                            </div>
                            <script src='/static/app.js'></script>
                        </main>
                </body>
        </html>
        """


@app.post("/api/v1/process-image", response_model=ImageResponse)
async def process_image(request: ImageRequest):
    try:
        if not landingai_service:
            raise HTTPException(
                status_code=500,
                detail="Landing AI service not initialized"
            )
        
        result = await landingai_service.process_image(
            image_data=request.image_data,
            image_type=request.image_type,
            task_type=request.task_type
        )
        
        return ImageResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Image processing failed: {str(e)}"
        )


@app.post("/api/v1/upload-image", response_model=ImageResponse)
async def upload_image(file: UploadFile = File(...), image_type: str = None, task_type: str = "defect_detection"):
    try:
        if not landingai_service:
            raise HTTPException(
                status_code=500,
                detail="Landing AI service not initialized"
            )
        
        image_bytes = await file.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        result = await landingai_service.process_image(
            image_data=image_base64,
            image_type=image_type,
            task_type=task_type
        )
        
        return ImageResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Image upload failed: {str(e)}"
        )


@app.post("/api/v1/validate-predictions")
async def validate_predictions(predictions: list):
    try:
        if not landingai_service:
            raise HTTPException(
                status_code=500,
                detail="Landing AI service not initialized"
            )
        
        result = await landingai_service.validate_predictions(predictions)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(e)}"
        )


@app.get("/api/v1/referrals")
async def get_referrals(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    urgency: Optional[str] = None,
    agent_segment: Optional[str] = None,
    schedule_status: Optional[str] = None
):
    try:
        _autopilot_tick_all()
        if not _db_ready():
            rows = _load_referrals_csv()
            if urgency:
                rows = [r for r in rows if (r.get("urgency") == urgency)]
            if agent_segment:
                rows = [r for r in rows if (r.get("agent_segment") == agent_segment)]
            if schedule_status:
                rows = [r for r in rows if (r.get("schedule_status") == schedule_status)]

            def _sort_key(r: dict):
                # Default to epoch-ish if missing
                return str(r.get("referral_received_date") or "")

            rows.sort(key=_sort_key, reverse=True)
            return rows[offset: offset + limit]
        
        query = "SELECT * FROM referrals WHERE 1=1"
        params = []
        
        if urgency:
            query += " AND urgency = %s"
            params.append(urgency)
        
        if agent_segment:
            query += " AND agent_segment = %s"
            params.append(agent_segment)
        
        if schedule_status:
            query += " AND schedule_status = %s"
            params.append(schedule_status)
        
        query += f" ORDER BY referral_received_date DESC LIMIT {limit} OFFSET {offset}"
        
        result = db_service.query(query, tuple(params) if params else None)
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result['message'])
        
        return result['data']
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Failed to fetch referrals: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch referrals: {str(e)}"
        )


@app.post("/api/v1/scheduling/apply")
async def apply_schedule(
    referral_id: str,
    caregiver_id: Optional[str] = None,
    scheduled_date: Optional[str] = None,
    schedule_status: str = "SCHEDULED",
):
    """Persist a scheduling decision so dashboard numbers update end-to-end.

    - If DB is available: updates `referrals` and writes to `referral_assignments`.
    - If DB is not available: writes to `data/scheduling_overrides.json` (demo mode).
    """
    try:
        rid = str(referral_id or "").strip()
        if not rid:
            raise HTTPException(status_code=400, detail="referral_id is required")

        sd = _safe_date(scheduled_date) or date.today()
        status = (schedule_status or "SCHEDULED").strip().upper()

        if _db_ready():
            # Ensure assignments table exists (safe no-op if already created)
            db_service.query(
                """
                CREATE TABLE IF NOT EXISTS referral_assignments (
                    referral_id VARCHAR(20) PRIMARY KEY,
                    caregiver_id VARCHAR(20),
                    schedule_status VARCHAR(50) DEFAULT 'SCHEDULED',
                    scheduled_date DATE,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Update referral scheduling state
            update_result = db_service.query(
                """
                UPDATE referrals
                SET schedule_status = %s,
                    scheduled_date = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE referral_id = %s
                """,
                (status, sd, rid),
            )
            if not update_result.get("success"):
                raise HTTPException(status_code=500, detail=update_result.get("message"))

            # Upsert assignment
            if caregiver_id:
                cg = str(caregiver_id).strip()
                db_service.query(
                    """
                    INSERT INTO referral_assignments (referral_id, caregiver_id, schedule_status, scheduled_date)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (referral_id)
                    DO UPDATE SET caregiver_id = EXCLUDED.caregiver_id,
                                  schedule_status = EXCLUDED.schedule_status,
                                  scheduled_date = EXCLUDED.scheduled_date,
                                  updated_at = CURRENT_TIMESTAMP
                    """,
                    (rid, cg, status, sd),
                )

            return {
                "success": True,
                "referral_id": rid,
                "schedule_status": status,
                "scheduled_date": sd.isoformat(),
                "assigned_caregiver_id": caregiver_id,
                "mode": "db",
            }

        # CSV/demo mode: write override
        overrides = _load_scheduling_overrides()
        overrides[rid] = {
            "schedule_status": status,
            "scheduled_date": sd.isoformat(),
            "assigned_caregiver_id": str(caregiver_id).strip() if caregiver_id else None,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
        _save_scheduling_overrides(overrides)

        # Keep journey timeline consistent with scheduling actions.
        if status == "SCHEDULED":
            _record_journey_event(rid, "SCHEDULED", source="scheduler")
        elif status == "COMPLETED":
            _record_journey_event(rid, "SERVICE_COMPLETED", source="scheduler")
        return {
            "success": True,
            "referral_id": rid,
            "schedule_status": status,
            "scheduled_date": sd.isoformat(),
            "assigned_caregiver_id": caregiver_id,
            "mode": "file",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply schedule: {str(e)}")


def _priority_score(referral: dict) -> int:
    """Heuristic priority scoring for scheduling queue."""
    score = 0
    urgency = str(referral.get("urgency") or "").strip().lower()
    segment = str(referral.get("agent_segment") or "").strip().upper()
    received = _safe_date(referral.get("referral_received_date"))
    auth_end = _safe_date(referral.get("auth_end_date"))
    contact_attempts = _safe_int(referral.get("contact_attempts"))
    units_remaining = _safe_int(referral.get("auth_units_remaining"))

    if urgency == "urgent":
        score += 100
    if segment == "RED":
        score += 50
    elif segment == "ORANGE":
        score += 25

    if received:
        days_waiting = max(0, (date.today() - received).days)
        score += min(days_waiting, 30)

    if auth_end:
        days_left = (auth_end - date.today()).days
        if days_left <= 3:
            score += 40
        elif days_left <= 7:
            score += 20

    if contact_attempts >= 3:
        score += 10
    if units_remaining <= 2 and units_remaining > 0:
        score += 10
    return int(score)


def _caregiver_capacity(caregiver: dict) -> int:
    et = str(caregiver.get("employment_type") or "").strip().lower()
    av = str(caregiver.get("availability") or "").strip().lower()
    # Simple demo capacities
    if "part" in et:
        base = 1
    elif "contract" in et:
        base = 2
    else:
        base = 3
    if "limited" in av:
        base = max(1, base - 1)
    return int(base)


def _compute_caregiver_load(assignments: dict, referrals: list[dict]) -> dict[str, int]:
    """Count active scheduled referrals per caregiver."""
    ref_by_id = {str(r.get("referral_id") or ""): r for r in referrals}
    load: dict[str, int] = {}
    for rid, a in (assignments or {}).items():
        if not isinstance(a, dict):
            continue
        cg = str(a.get("caregiver_id") or "").strip()
        if not cg:
            continue
        status = str(a.get("schedule_status") or "").strip().upper()
        if status != "SCHEDULED":
            continue
        r = ref_by_id.get(str(rid))
        if not r:
            continue
        if str(r.get("service_complete") or "").strip().upper() == "Y":
            continue
        load[cg] = load.get(cg, 0) + 1
    return load


def _derive_journey_stage(r: dict) -> str:
    """Derive a human-demo-friendly stage for board view.
    
    Prioritizes explicitly set journey_stage from database, falls back to derived logic.
    """
    try:
        # Check if journey_stage is explicitly set in database
        stored_stage = str(r.get("journey_stage") or "").strip().upper()
        if stored_stage and stored_stage not in ("", "INTAKE_RECEIVED"):
            # Map stored stages to board stages
            stage_mapping = {
                "DOCS_COMPLETED": "READY_TO_SCHEDULE",
                "HOME_ASSESSMENT_SCHEDULED": "HOME_ASSESSMENT_PENDING",
                "HOME_ASSESSMENT_COMPLETED": "READY_TO_SCHEDULE",
                "SERVICE_STARTED": "SCHEDULED",
                "READY_TO_BILL": "READY_TO_BILL",
                "SERVICE_COMPLETED": "COMPLETED",
            }
            if stored_stage in stage_mapping:
                return stage_mapping[stored_stage]
            if stored_stage in ("SCHEDULED", "COMPLETED", "AUTH_PENDING", "AUTH_ISSUE", "DOCS_PENDING", "HOME_ASSESSMENT_PENDING", "READY_TO_SCHEDULE", "IN_PROGRESS"):
                return stored_stage

        # Terminal states from data
        if str(r.get("service_complete") or "").strip().upper() == "Y" or str(r.get("schedule_status") or "").strip().upper() == "COMPLETED":
            return "COMPLETED"
        if str(r.get("ready_to_bill") or "").strip().upper() == "Y":
            return "READY_TO_BILL"
        if str(r.get("schedule_status") or "").strip().upper() == "SCHEDULED":
            return "SCHEDULED"

        insurance_ok = str(r.get("insurance_active") or "").strip().upper() == "Y"
        auth_required = str(r.get("auth_required") or "").strip().upper() == "Y"
        auth_status = str(r.get("auth_status") or "").strip().upper()
        auth_ok = (not auth_required) or (auth_status == "APPROVED")

        if insurance_ok and auth_required and auth_status not in ("APPROVED", ""):
            # DENIED/EXPIRED/etc
            return "AUTH_ISSUE"
        if insurance_ok and auth_required and auth_status != "APPROVED":
            return "AUTH_PENDING"

        docs_complete = str(r.get("docs_complete") or "").strip().upper() == "Y"
        if not docs_complete:
            return "DOCS_PENDING"

        ha_done = str(r.get("home_assessment_done") or "").strip().upper() == "Y"
        if not ha_done:
            return "HOME_ASSESSMENT_PENDING"

        sched_status = str(r.get("schedule_status") or "").strip().upper()
        if sched_status == "NOT_SCHEDULED" and insurance_ok and auth_ok:
            return "READY_TO_SCHEDULE"

        return "IN_PROGRESS"
    except Exception:
        return "IN_PROGRESS"


@app.get("/api/v1/journey/board")
async def journey_board(limit_per_stage: int = Query(50, ge=5, le=200)):
    """Kanban-style board data: all referrals grouped by derived stage."""
    try:
        _autopilot_tick_all()
        if _db_ready():
            res = db_service.query("SELECT * FROM referrals")
            if not res.get("success"):
                raise HTTPException(status_code=500, detail=res.get("message"))
            referrals = res.get("data") or []
        else:
            referrals = _load_referrals_csv()

        stage_order = [
            ("AUTH_PENDING", "Authorization Pending"),
            ("AUTH_ISSUE", "Authorization Issue"),
            ("DOCS_PENDING", "Docs Pending"),
            ("HOME_ASSESSMENT_PENDING", "Home Assessment Pending"),
            ("READY_TO_SCHEDULE", "Ready to Schedule"),
            ("SCHEDULED", "Scheduled"),
            ("READY_TO_BILL", "Ready to Bill"),
            ("COMPLETED", "Completed"),
            ("IN_PROGRESS", "In Progress"),
        ]

        buckets: dict[str, list[dict]] = {k: [] for k, _ in stage_order}
        for r in referrals:
            stage = _derive_journey_stage(r)
            if stage not in buckets:
                buckets.setdefault(stage, []).append(r)
            else:
                buckets[stage].append(r)

        # Sort each bucket by urgency then received date
        def _urg_key(rr: dict) -> int:
            u = str(rr.get("urgency") or "").strip().lower()
            return 0 if u == "urgent" else 1

        def _date_key(rr: dict) -> str:
            return str(rr.get("referral_received_date") or "")

        stages = []
        for key, label in stage_order:
            rows = buckets.get(key) or []
            rows.sort(key=lambda rr: (_urg_key(rr), _date_key(rr)))
            trimmed = rows[:limit_per_stage]
            stages.append(
                {
                    "stage": key,
                    "label": label,
                    "count": len(rows),
                    "referrals": [
                        {
                            "referral_id": rr.get("referral_id"),
                            "urgency": rr.get("urgency"),
                            "agent_segment": rr.get("agent_segment"),
                            "patient_city": rr.get("patient_city"),
                            "payer": rr.get("payer"),
                            "schedule_status": rr.get("schedule_status"),
                            "auth_status": rr.get("auth_status"),
                            "agent_next_action": rr.get("agent_next_action"),
                            "referral_received_date": rr.get("referral_received_date"),
                        }
                        for rr in trimmed
                        if rr.get("referral_id")
                    ],
                }
            )

        return {
            "success": True,
            "stages": stages,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build journey board: {str(e)}")


@app.get("/api/v1/ops/summary")
async def ops_summary(limit: int = Query(10, ge=1, le=50)):
    """Live ops KPIs for the React frontend (active clients, urgent, last-week leads, priority queue, pairings)."""
    try:
        _autopilot_tick_all()
        today = date.today()
        last_7d = today - timedelta(days=7)

        if _db_ready():
            referrals_result = db_service.query("SELECT * FROM referrals")
            if not referrals_result.get("success"):
                raise HTTPException(status_code=500, detail=referrals_result.get("message"))
            referrals = referrals_result.get("data") or []

            caregivers_result = db_service.query("SELECT * FROM caregivers")
            caregivers = caregivers_result.get("data") if caregivers_result.get("success") else []

            # Optional assignments table
            assignments = {}
            assign_result = db_service.query(
                """
                SELECT referral_id, caregiver_id, schedule_status, scheduled_date
                FROM referral_assignments
                """
            )
            if assign_result.get("success"):
                for r in assign_result.get("data") or []:
                    assignments[str(r.get("referral_id"))] = r
        else:
            referrals = _load_referrals_csv()
            caregivers = _load_caregivers_csv()
            overrides = _load_scheduling_overrides()
            assignments = {
                rid: {
                    "referral_id": rid,
                    "caregiver_id": o.get("assigned_caregiver_id"),
                    "schedule_status": o.get("schedule_status"),
                    "scheduled_date": o.get("scheduled_date"),
                }
                for rid, o in overrides.items()
                if isinstance(o, dict)
            }

        def _is_active(r: dict) -> bool:
            return str(r.get("service_complete") or "").strip().upper() == "N"

        def _is_pending_sched(r: dict) -> bool:
            return (
                str(r.get("schedule_status") or "").strip() == "NOT_SCHEDULED"
                and str(r.get("insurance_active") or "").strip().upper() == "Y"
                and (
                    str(r.get("auth_required") or "").strip().upper() == "N"
                    or str(r.get("auth_status") or "").strip().upper() == "APPROVED"
                )
                and _is_active(r)
            )

        total_referrals = len(referrals)
        total_caregivers = len(caregivers)
        active_clients = sum(1 for r in referrals if _is_active(r))
        completed_clients = sum(1 for r in referrals if str(r.get("service_complete") or "").strip().upper() == "Y")
        scheduled_clients = sum(1 for r in referrals if str(r.get("schedule_status") or "").strip() == "SCHEDULED")
        pending_scheduling = sum(1 for r in referrals if _is_pending_sched(r))
        active_caregivers = sum(1 for c in caregivers if str(c.get("active") or "").strip().upper() == "Y")

        caregiver_load = _compute_caregiver_load(assignments, referrals)
        caregivers_by_id = {str(c.get("caregiver_id") or "").strip(): c for c in caregivers}
        available_caregivers = 0
        busy_caregivers = 0
        for cg_id, c in caregivers_by_id.items():
            if not cg_id:
                continue
            if str(c.get("active") or "").strip().upper() != "Y":
                continue
            cap = _caregiver_capacity(c)
            used = caregiver_load.get(cg_id, 0)
            if used >= cap:
                busy_caregivers += 1
            else:
                available_caregivers += 1

        leads_last_7d = [r for r in referrals if (_safe_date(r.get("referral_received_date")) or date(1970, 1, 1)) >= last_7d]
        leads_last_7d_count = len(leads_last_7d)
        leads_last_7d_urgent = [r for r in leads_last_7d if str(r.get("urgency") or "").strip().lower() == "urgent"]

        urgent_pending = [r for r in referrals if _is_pending_sched(r) and str(r.get("urgency") or "").strip().lower() == "urgent"]
        urgent_pending_count = len(urgent_pending)

        # Pairings: scheduled/assigned referrals
        assigned_pairs = [a for a in assignments.values() if (a.get("caregiver_id") or a.get("caregiver_id") == 0)]
        unique_caregivers_paired = len({str(a.get("caregiver_id")) for a in assigned_pairs if a.get("caregiver_id")})
        paired_referrals = len({str(a.get("referral_id")) for a in assigned_pairs if a.get("referral_id")})

        queue = [r for r in referrals if _is_pending_sched(r)]
        for r in queue:
            r["_priority_score"] = _priority_score(r)
        queue.sort(key=lambda r: (-(r.get("_priority_score") or 0), str(r.get("referral_received_date") or "")))
        top = queue[:limit]

        def _priority_label(score: int) -> str:
            if score >= 130:
                return "HIGH"
            if score >= 80:
                return "MEDIUM"
            return "LOW"

        priority_queue = [
            {
                "referral_id": r.get("referral_id"),
                "urgency": r.get("urgency"),
                "agent_segment": r.get("agent_segment"),
                "patient_city": r.get("patient_city"),
                "payer": r.get("payer"),
                "schedule_status": r.get("schedule_status"),
                "auth_units_remaining": r.get("auth_units_remaining"),
                "contact_attempts": r.get("contact_attempts"),
                "referral_received_date": r.get("referral_received_date"),
                "score": int(r.get("_priority_score") or 0),
                "priority": _priority_label(int(r.get("_priority_score") or 0)),
            }
            for r in top
        ]

        urgent_preview = [
            {
                "referral_id": r.get("referral_id"),
                "patient_city": r.get("patient_city"),
                "agent_segment": r.get("agent_segment"),
                "auth_units_remaining": r.get("auth_units_remaining"),
                "referral_received_date": r.get("referral_received_date"),
            }
            for r in urgent_pending[: min(10, len(urgent_pending))]
        ]

        return {
            "kpis": {
                "total_referrals": total_referrals,
                "active_clients": active_clients,
                "completed_clients": completed_clients,
                "scheduled_clients": scheduled_clients,
                "pending_scheduling": pending_scheduling,
                "total_caregivers": total_caregivers,
                "active_caregivers": active_caregivers,
                "available_caregivers": available_caregivers,
                "busy_caregivers": busy_caregivers,
                "paired_referrals": paired_referrals,
                "unique_caregivers_paired": unique_caregivers_paired,
                "leads_last_7d": leads_last_7d_count,
                "leads_last_7d_urgent": len(leads_last_7d_urgent),
                "urgent_pending": urgent_pending_count,
            },
            "urgent_pending_preview": urgent_preview,
            "priority_queue": priority_queue,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build ops summary: {str(e)}")


@app.get("/api/v1/caregivers", response_model=List[CaregiverResponse])
async def get_caregivers(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    city: Optional[str] = None,
    active: Optional[str] = None,
    skills: Optional[str] = None
):
    try:
        if not _db_ready():
            rows = _load_caregivers_csv()

            # Add derived load/capacity fields so caregiver counts fluctuate with scheduling
            referrals = _load_referrals_csv()
            overrides = _load_scheduling_overrides()
            assignments = {
                rid: {
                    "referral_id": rid,
                    "caregiver_id": o.get("assigned_caregiver_id"),
                    "schedule_status": o.get("schedule_status"),
                    "scheduled_date": o.get("scheduled_date"),
                }
                for rid, o in overrides.items()
                if isinstance(o, dict)
            }
            load = _compute_caregiver_load(assignments, referrals)

            for c in rows:
                cg_id = str(c.get("caregiver_id") or "").strip()
                cap = _caregiver_capacity(c)
                used = load.get(cg_id, 0)
                c["current_assignments"] = used
                c["available_slots"] = max(0, cap - used)
                c["capacity"] = cap
                c["availability_status"] = "BUSY" if used >= cap else "AVAILABLE"

            if city:
                rows = [r for r in rows if (r.get("city") == city)]
            if active:
                rows = [r for r in rows if (r.get("active") == active)]
            if skills:
                sk = skills.strip().lower()
                rows = [r for r in rows if sk in str(r.get("skills") or "").lower()]
            rows.sort(key=lambda r: str(r.get("caregiver_id") or ""))
            return rows[offset: offset + limit]
        
        # Select only needed columns
        query = """SELECT caregiver_id, gender, date_of_birth, age, primary_language, skills, 
                   employment_type, availability, city, active 
                   FROM caregivers WHERE 1=1"""
        params = []
        
        if city:
            query += " AND city = %s"
            params.append(city)
        
        if active:
            query += " AND active = %s"
            params.append(active)
        
        if skills:
            query += " AND skills LIKE %s"
            params.append(f"%{skills}%")
        
        query += f" ORDER BY caregiver_id LIMIT {limit} OFFSET {offset}"
        
        result = db_service.query(query, tuple(params) if params else None)
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result['message'])
        
        return result['data']
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch caregivers: {str(e)}"
        )


@app.get("/api/v1/stats", response_model=DataStatsResponse)
async def get_stats():
    try:
        if not _db_ready():
            referrals = _load_referrals_csv()
            caregivers = _load_caregivers_csv()
            stats = {
                "total_referrals": len(referrals),
                "active_referrals": sum(1 for r in referrals if str(r.get("service_complete") or "").strip().upper() == "N"),
                "total_caregivers": len(caregivers),
                "active_caregivers": sum(1 for c in caregivers if str(c.get("active") or "").strip().upper() == "Y"),
            }
            return stats
        
        result = db_service.get_table_stats()
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result['message'])
        
        return result['stats']
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch stats: {str(e)}"
        )


@app.get("/api/v1/dashboard-metrics", response_model=DashboardMetricsResponse)
async def get_dashboard_metrics():
    try:
        return _build_dashboard_metrics()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch dashboard metrics: {str(e)}"
        )


@app.post("/api/v1/agent/process-referral")
async def process_referral_with_agents(referral_id: str):
    """
    Run 3-agent workflow for a specific referral:
    1. Validation Agent - Check if referral is good
    2. Matching Agent - Find caregivers in the area
    3. Scheduling Agent - Create schedule recommendation
    """
    try:
        if not agent_workflow:
            raise HTTPException(status_code=500, detail="Agent Workflow not initialized")

        if _db_ready():
            # Get referral data
            result = db_service.query(
                "SELECT * FROM referrals WHERE referral_id = %s",
                (referral_id,)
            )

            if not result['success'] or not result['data']:
                raise HTTPException(
                    status_code=404,
                    detail=f"Referral {referral_id} not found"
                )

            referral = result['data'][0]

            # Get caregivers in same city
            city = referral.get('patient_city')
            caregiver_result = db_service.query(
                "SELECT * FROM caregivers WHERE city = %s AND active = 'Y'",
                (city,)
            )
            caregivers = caregiver_result['data'] if caregiver_result['success'] else []
        else:
            referrals = _load_referrals_csv()
            referral = next((r for r in referrals if r.get("referral_id") == referral_id), None)
            if not referral:
                raise HTTPException(status_code=404, detail=f"Referral {referral_id} not found")
            city = referral.get("patient_city")
            caregivers = [c for c in _load_caregivers_csv() if c.get("city") == city and str(c.get("active") or "").upper() == "Y"]
        
        # Run agent workflow
        workflow_result = agent_workflow.process_referral(referral, caregivers)

        # Attach compliance guardrails (if any) so agents/UI can reference them
        try:
            guardrails = _load_compliance_docs()
            if guardrails:
                top = []
                for d in guardrails[:5]:
                    top.append(
                        {
                            "compliance_id": d.get("compliance_id"),
                            "source_filename": d.get("source_filename"),
                            "created_at": d.get("created_at"),
                            "excerpt": d.get("excerpt"),
                        }
                    )
                if isinstance(workflow_result, dict):
                    workflow_result["compliance_guardrails"] = {"count": len(guardrails), "top": top}
                    v = workflow_result.get("validation")
                    if isinstance(v, dict):
                        warnings = v.get("warnings")
                        if not isinstance(warnings, list):
                            warnings = []
                            v["warnings"] = warnings
                        warnings.append(
                            f"Compliance guardrails loaded: {len(guardrails)} document(s). Review before scheduling."
                        )
        except Exception:
            pass
        
        return {
            "success": True,
            "workflow_result": workflow_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent workflow failed: {str(e)}"
        )


@app.get("/api/v1/agent/pending-referrals")
async def get_pending_referrals():
    """
    Get referrals that are waiting for scheduling
    Uses rules engine to filter, then AI Sorting Agent to intelligently prioritize
    """
    try:
        if not agent_workflow:
            raise HTTPException(status_code=500, detail="Agent Workflow not initialized")
        
        # Get limit from agent config (default to 50 if not available)
        max_pending = 50
        try:
            if hasattr(agent_workflow, 'scheduling_agent') and hasattr(agent_workflow.scheduling_agent, 'max_pending_referrals'):
                max_pending = agent_workflow.scheduling_agent.max_pending_referrals
        except:
            pass
        
        if _db_ready():
            # Step 1: Use rules engine to build WHERE clause (filtering only)
            print(f"\n{'='*60}")
            print("STEP 1: APPLYING FILTER RULES")
            print(f"{'='*60}")

            sql_parts = rules_engine.generate_sql_where_clause()
            print(f"WHERE Clause: {sql_parts.get('where_clause')}")
            print(f"{'='*60}\n")

            # Build query WITHOUT ORDER BY (sorting will be done by AI)
            query = "SELECT * FROM referrals"
            if sql_parts.get("where_clause"):
                query += f" WHERE {sql_parts['where_clause']}"

            # Get more records than needed so AI can pick the best ones
            query += f" LIMIT {max_pending * 2}"

            result = db_service.query(query)
            if not result.get("success"):
                raise HTTPException(status_code=500, detail=result.get("message"))

            # Step 2: Use AI Sorting Agent to intelligently prioritize
            sorted_referrals = sorting_agent.sort_referrals(result.get("data") or [])

            # Step 3: Return top N after AI sorting
            final_referrals = sorted_referrals[:max_pending]
            return {
                "success": True,
                "count": len(final_referrals),
                "referrals": final_referrals,
            }

        # File/demo mode fallback
        referrals = _load_referrals_csv()

        def _is_ok(r: dict) -> bool:
            return (
                str(r.get("schedule_status") or "") == "NOT_SCHEDULED"
                and str(r.get("insurance_active") or "").upper() == "Y"
                and (
                    str(r.get("auth_required") or "").upper() == "N"
                    or str(r.get("auth_status") or "").upper() == "APPROVED"
                )
                and str(r.get("service_complete") or "").upper() == "N"
            )

        filtered = [r for r in referrals if _is_ok(r)]

        def _urgency_rank(r: dict) -> int:
            return 1 if str(r.get("urgency") or "") == "Urgent" else 2

        filtered.sort(key=lambda r: (_urgency_rank(r), str(r.get("referral_received_date") or "")))
        filtered = filtered[:max_pending]
        return {
            "success": True,
            "count": len(filtered),
            "referrals": filtered,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch pending referrals: {str(e)}"
        )


@app.post("/api/v1/agent/reload-rules")
async def reload_scheduler_rules():
    """
    Reload scheduler rules from config/scheduler_rules.txt
    Allows updating rules without restarting the server
    """
    try:
        rules_engine.reload_rules()
        sql_parts = rules_engine.generate_sql_where_clause()
        
        return {
            "success": True,
            "message": "Scheduler rules reloaded successfully",
            "rules_preview": {
                "where_clause": sql_parts.get('where_clause'),
                "order_by": sql_parts.get('order_by')
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reload rules: {str(e)}"
        )


@app.post("/api/v1/crew/process-referral")
async def process_referral_with_crew(referral_id: str):
    """
    Process a referral using Crew AI workflow
    Runs validation, matching, and compliance agents
    """
    try:
        if not crew_workflow:
            raise HTTPException(
                status_code=503,
                detail="Crew AI workflow not initialized. Check SWARMS_API_KEY in environment."
            )
        
        if not db_service:
            raise HTTPException(status_code=500, detail="Database service not initialized")
        
        # Fetch referral data
        referral_result = db_service.query(
            f"SELECT * FROM referrals WHERE referral_id = '{referral_id}'"
        )
        
        if not referral_result['success'] or not referral_result['data']:
            raise HTTPException(status_code=404, detail=f"Referral {referral_id} not found")
        
        referral_data = referral_result['data'][0]
        
        # Fetch available caregivers
        caregivers_result = db_service.query("SELECT * FROM caregivers WHERE available = 'Y'")
        caregivers = caregivers_result.get('data', []) if caregivers_result['success'] else []
        
        # Process through Crew AI workflow
        result = crew_workflow.process_referral(referral_data, caregivers)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Crew AI processing failed: {str(e)}"
        )


@app.post("/api/v1/crew/process-batch")
async def process_batch_with_crew(limit: int = 10):
    """
    Process multiple referrals in batch using Crew AI
    """
    try:
        if not crew_workflow:
            raise HTTPException(
                status_code=503,
                detail="Crew AI workflow not initialized. Check SWARMS_API_KEY in environment."
            )
        
        if not db_service:
            raise HTTPException(status_code=500, detail="Database service not initialized")
        
        # Get pending referrals
        referrals_result = db_service.query(f"""
            SELECT * FROM referrals 
            WHERE schedule_status = 'NOT_SCHEDULED'
              AND insurance_active = 'Y'
            LIMIT {limit}
        """)
        
        if not referrals_result['success']:
            raise HTTPException(status_code=500, detail="Failed to fetch referrals")
        
        referrals = referrals_result.get('data', [])
        
        # Get caregivers
        caregivers_result = db_service.query("SELECT * FROM caregivers WHERE available = 'Y'")
        caregivers = caregivers_result.get('data', []) if caregivers_result['success'] else []
        
        # Process batch
        results = crew_workflow.process_batch_referrals(referrals, caregivers)
        
        return {
            "success": True,
            "processed_count": len(results),
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch processing failed: {str(e)}"
        )


@app.get("/api/v1/crew/history")
async def get_crew_execution_history(limit: int = 20):
    """
    Get Crew AI execution history for monitoring
    Shows recent agent workflow runs with status and duration
    """
    try:
        if not crew_workflow:
            raise HTTPException(
                status_code=503,
                detail="Crew AI workflow not initialized"
            )
        
        history = crew_workflow.get_execution_history(limit)
        
        return {
            "success": True,
            "count": len(history),
            "executions": history
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch history: {str(e)}"
        )


@app.get("/api/v1/crew/stats")
async def get_crew_stats():
    """
    Get Crew AI workflow statistics
    Returns: total runs, success rate, average duration, etc.
    """
    try:
        if not crew_workflow:
            raise HTTPException(
                status_code=503,
                detail="Crew AI workflow not initialized"
            )
        
        stats = crew_workflow.get_stats()
        
        return {
            "success": True,
            "stats": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch stats: {str(e)}"
        )


@app.post("/api/v1/schedule/confirm")
async def schedule_referral(referral_id: str, caregiver_id: Optional[str] = None):
    """
    Schedule a referral and send confirmation email
    
    Args:
        referral_id: ID of the referral to schedule
        caregiver_id: Optional caregiver assignment
        
    Returns:
        Scheduling result with email confirmation status
    """
    try:
        print(f"\n{'='*60}")
        print(f"SCHEDULE REQUEST RECEIVED")
        print(f"Referral ID: {referral_id}")
        print(f"Caregiver ID: {caregiver_id}")
        print(f"{'='*60}\n")
        
        if not db_service:
            raise HTTPException(status_code=500, detail="Database service not initialized")
        
        # Fetch referral data
        referral_result = db_service.query(
            f"SELECT * FROM referrals WHERE referral_id = '{referral_id}'"
        )
        
        print(f"Referral query result: {referral_result.get('success')}")
        
        if not referral_result['success'] or not referral_result['data']:
            raise HTTPException(status_code=404, detail=f"Referral {referral_id} not found")
        
        referral_data = referral_result['data'][0]
        print(f"Referral data retrieved: {referral_data.get('referral_id')}")
        
        # Fetch caregiver data if provided
        caregiver_data = None
        if caregiver_id:
            caregiver_result = db_service.query(
                f"SELECT * FROM caregivers WHERE caregiver_id = '{caregiver_id}'"
            )
            if caregiver_result['success'] and caregiver_result['data']:
                caregiver_data = caregiver_result['data'][0]
        
        # Update referral status to SCHEDULED
        print(f"Updating referral status to SCHEDULED...")
        update_result = db_service.query(f"""
            UPDATE referrals 
            SET schedule_status = 'SCHEDULED'
            WHERE referral_id = '{referral_id}'
        """)
        
        print(f"Update result: {update_result}")
        
        if not update_result['success']:
            error_msg = update_result.get('message', 'Unknown error')
            print(f"Database update failed: {error_msg}")
            raise HTTPException(status_code=500, detail=f"Failed to update referral status: {error_msg}")
        
        # Send scheduling confirmation email
        print(f"Sending email confirmation...")
        print(f"Email service available: {email_service is not None}")
        email_result = email_service.send_scheduling_confirmation(
            referral_data=referral_data,
            caregiver_data=caregiver_data
        )
        
        print(f"Email result: {email_result}")
        
        return {
            "success": True,
            "referral_id": referral_id,
            "status": "SCHEDULED",
            "caregiver_assigned": caregiver_id,
            "email_sent": email_result.get("success", False),
            "email_details": email_result,
            "message": "Referral scheduled successfully and confirmation email sent"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"\n{'='*60}")
        print(f"SCHEDULE ERROR:")
        print(f"{'='*60}")
        print(error_trace)
        print(f"{'='*60}\n")
        raise HTTPException(
            status_code=500,
            detail=f"Scheduling failed: {str(e)}"
        )


@app.post("/api/v1/email/send-notification")
async def send_email_notification(
    referral_id: str,
    notification_type: str = "workflow_update",
    details: Optional[str] = None
):
    """
    Send email notification for workflow updates
    
    Args:
        referral_id: Referral ID
        notification_type: Type of notification
        details: Additional details
    """
    try:
        if notification_type == "workflow_update":
            result = email_service.send_workflow_notification(
                referral_id=referral_id,
                workflow_status="Updated",
                details=details or "Workflow status has been updated"
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid notification type")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send notification: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
