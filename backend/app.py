from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List, Optional
import sys
from pathlib import Path
import base64

sys.path.insert(0, str(Path(__file__).parent))

from src.models.schemas import ImageRequest, ImageResponse, ErrorResponse
from src.models.data_schemas import CaregiverResponse, ReferralResponse, DataStatsResponse
from src.services.landingai_service import LandingAIService
from src.services.agent_workflow import AgentWorkflow
from database.db_service import DatabaseService


landingai_service = None
db_service = None
agent_workflow = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global landingai_service, db_service, agent_workflow
    landingai_service = LandingAIService()
    print("Landing AI service initialized successfully")
    
    db_service = DatabaseService()
    result = db_service.connect()
    if result['success']:
        print("Database service initialized successfully")
    else:
        print(f"Warning: Database connection failed - {result['message']}")
    
    agent_workflow = AgentWorkflow()
    print("Agent Workflow initialized successfully")
    
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
        if not db_service:
            raise HTTPException(
                status_code=500,
                detail="Database service not initialized"
            )
        
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


@app.get("/api/v1/caregivers", response_model=List[CaregiverResponse])
async def get_caregivers(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    city: Optional[str] = None,
    active: Optional[str] = None,
    skills: Optional[str] = None
):
    try:
        if not db_service:
            raise HTTPException(
                status_code=500,
                detail="Database service not initialized"
            )
        
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
        if not db_service:
            raise HTTPException(
                status_code=500,
                detail="Database service not initialized"
            )
        
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


@app.post("/api/v1/agent/process-referral")
async def process_referral_with_agents(referral_id: str):
    """
    Run 3-agent workflow for a specific referral:
    1. Validation Agent - Check if referral is good
    2. Matching Agent - Find caregivers in the area
    3. Scheduling Agent - Create schedule recommendation
    """
    try:
        if not db_service or not agent_workflow:
            raise HTTPException(
                status_code=500,
                detail="Services not initialized"
            )
        
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
        
        # Run agent workflow
        workflow_result = agent_workflow.process_referral(referral, caregivers)
        
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
    Limit is loaded from agent_config.yaml
    """
    try:
        if not db_service or not agent_workflow:
            raise HTTPException(
                status_code=500,
                detail="Services not initialized"
            )
        
        # Get limit from agent config (default to 50 if not available)
        max_pending = 50
        try:
            if hasattr(agent_workflow, 'scheduling_agent') and hasattr(agent_workflow.scheduling_agent, 'max_pending_referrals'):
                max_pending = agent_workflow.scheduling_agent.max_pending_referrals
        except:
            pass
        
        result = db_service.query(f"""
            SELECT * FROM referrals 
            WHERE schedule_status = 'NOT_SCHEDULED'
              AND insurance_active = 'Y'
              AND (auth_required = 'N' OR auth_status = 'APPROVED')
              AND service_complete = 'N'
            ORDER BY 
                CASE WHEN urgency = 'Urgent' THEN 1 ELSE 2 END,
                referral_received_date ASC
            LIMIT {max_pending}
        """)
        
        if not result['success']:
            raise HTTPException(status_code=500, detail=result['message'])
        
        return {
            "success": True,
            "count": len(result['data']),
            "referrals": result['data']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch pending referrals: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
