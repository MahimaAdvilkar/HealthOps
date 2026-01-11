from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi import Response
from starlette.staticfiles import StaticFiles
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys
from pathlib import Path
import base64
import csv
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from src.models.schemas import ImageRequest, ImageResponse, ErrorResponse
from src.services.landingai_service import LandingAIService


landingai_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global landingai_service
    landingai_service = LandingAIService()
    print("Landing AI service initialized successfully")
    yield
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
    norm_rows = _parse_csv_dicts(DOC_EXTRACT_DIR / "normalized_summary.csv")
    indiv_rows = _parse_csv_dicts(DOC_EXTRACT_DIR / "individual" / "summary_individual.csv")
    outcomes_rows = _parse_csv_dicts(DOC_EXTRACT_DIR / "pipeline_outcomes.csv")
    referrals_rows = _parse_csv_dicts(REPO_ROOT / "data" / "referrals_synthetic.csv")
    caregivers_rows = _parse_csv_dicts(REPO_ROOT / "data" / "caregivers_synthetic.csv")
    # Aggregates from normalized summary
    total_referrals = len(norm_rows)
    auth_required_yes = sum(1 for r in norm_rows if str(r.get("authorization_required", "")).strip().lower() in ("yes", "true"))
    auth_approved = sum(1 for r in norm_rows if str(r.get("authorization_status", "")).strip().lower() == "approved")
    ready_to_bill = sum(1 for r in norm_rows if str(r.get("ready_to_bill", "")).strip().lower() in ("yes", "true"))
    units_authorized = sum(_safe_int(r.get("authorized_units", 0)) for r in norm_rows)
    units_delivered = sum(_safe_int(r.get("units_delivered", 0)) for r in norm_rows)

    # Aggregates from individual summary
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

    # Aggregates from pipeline outcomes
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

    cards_html = _render_cards(cards)

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
                                        <tr><td>Referral Received</td><td>{outcome_stats['referral_received']}</td></tr>
                                        <tr><td>Intake Complete</td><td>{outcome_stats['intake_complete']}</td></tr>
                                        <tr><td>Assessment Complete</td><td>{outcome_stats['assessment_complete']}</td></tr>
                                        <tr><td>Eligibility Verified</td><td>{outcome_stats['eligibility_verified']}</td></tr>
                                        <tr><td>Auth Required</td><td>{outcome_stats['auth_required']}</td></tr>
                                        <tr><td>Auth Approved</td><td>{outcome_stats['auth_approved']}</td></tr>
                                        <tr><td>Ready To Schedule</td><td>{outcome_stats['ready_to_schedule']}</td></tr>
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
