from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class DocumentRequest(BaseModel):
    document_content: str = Field(..., description="Content of the document to process")
    document_type: Optional[str] = Field(None, description="Type of document (optional)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class DocumentResponse(BaseModel):
    success: bool = Field(..., description="Whether processing was successful")
    message: str = Field(..., description="Status message")
    extracted_data: Optional[Dict[str, Any]] = Field(None, description="Extracted information from document")
    processing_time: Optional[float] = Field(None, description="Time taken to process in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    

class ErrorResponse(BaseModel):
    success: bool = Field(default=False, description="Always False for errors")
    message: str = Field(..., description="Error message")
    error_type: Optional[str] = Field(None, description="Type of error")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
