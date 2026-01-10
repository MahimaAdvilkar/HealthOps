from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.models.schemas import DocumentRequest, DocumentResponse, ErrorResponse
from src.services.langchain_service import LangChainService


langchain_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global langchain_service
    langchain_service = LangChainService()
    print("LangChain service initialized successfully")
    yield
    print("Shutting down...")


app = FastAPI(
    title="HealthOps API",
    description="LangChain-powered document processing for healthcare operations",
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
        "message": "HealthOps API - LangChain Document Processing",
        "status": "active",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "langchain_document_processor"
    }


@app.post("/api/v1/process-document", response_model=DocumentResponse)
async def process_document(request: DocumentRequest):
    try:
        if not langchain_service:
            raise HTTPException(
                status_code=500,
                detail="LangChain service not initialized"
            )
        
        result = await langchain_service.process_document(
            document_content=request.document_content,
            document_type=request.document_type
        )
        
        return DocumentResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(e)}"
        )


@app.post("/api/v1/validate-extraction")
async def validate_extraction(extracted_data: dict):
    try:
        if not langchain_service:
            raise HTTPException(
                status_code=500,
                detail="LangChain service not initialized"
            )
        
        result = await langchain_service.validate_extraction(extracted_data)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
