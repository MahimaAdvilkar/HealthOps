from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys
from pathlib import Path
import base64

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
                <table border=1 cellspacing=0 cellpadding=6>
                    <thead><tr>{th}</tr></thead>
                    <tbody>
                        {trs}
                    </tbody>
                </table>
                """
        except Exception as e:
                return f"<h2>{title}</h2><p>Error rendering table: {e}</p>"


@app.get("/ui/summary", response_class=HTMLResponse)
async def ui_summary():
        path = DOC_EXTRACT_DIR / "normalized_summary.csv"
        content = _csv_to_html_table(path, "Normalized Referral Summary")
        return f"""
        <html>
            <head><title>HealthOps Summary</title></head>
            <body>
                <h1>HealthOps Document Parsing</h1>
                <nav>
                    <a href='/ui/summary'>Summary</a> |
                    <a href='/ui/individual'>Per-Document Summary</a>
                </nav>
                {content}
            </body>
        </html>
        """


@app.get("/ui/individual", response_class=HTMLResponse)
async def ui_individual():
        path = DOC_EXTRACT_DIR / "individual" / "summary_individual.csv"
        content = _csv_to_html_table(path, "Per-Document Parsing Summary")
        return f"""
        <html>
            <head><title>HealthOps Per-Document Summary</title></head>
            <body>
                <h1>HealthOps Document Parsing</h1>
                <nav>
                    <a href='/ui/summary'>Summary</a> |
                    <a href='/ui/individual'>Per-Document Summary</a>
                </nav>
                {content}
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
