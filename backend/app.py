from fastapi import FastAPI, HTTPException, UploadFile, File
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
