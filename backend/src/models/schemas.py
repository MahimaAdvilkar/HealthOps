from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class ImageRequest(BaseModel):
    image_data: str = Field(..., description="Base64 encoded image data")
    image_type: Optional[str] = Field(None, description="Type of medical image (X-ray, MRI, CT, etc.)")
    task_type: str = Field(default="defect_detection", description="Type of task (defect_detection, classification, visual_qa)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class Prediction(BaseModel):
    label: str = Field(..., description="Prediction label/class")
    confidence: float = Field(..., description="Confidence score (0-1)")
    bounding_box: Optional[Dict[str, Any]] = Field(None, description="Bounding box coordinates")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional prediction metadata")


class ImageResponse(BaseModel):
    success: bool = Field(..., description="Whether processing was successful")
    message: str = Field(..., description="Status message")
    predictions: Optional[List[Prediction]] = Field(None, description="List of predictions from the model")
    total_detections: int = Field(default=0, description="Total number of detections")
    image_type: Optional[str] = Field(None, description="Type of image processed")
    task_type: Optional[str] = Field(None, description="Type of task performed")
    processing_time: Optional[float] = Field(None, description="Time taken to process in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class ErrorResponse(BaseModel):
    success: bool = Field(default=False, description="Always False for errors")
    message: str = Field(..., description="Error message")
    error_type: Optional[str] = Field(None, description="Type of error")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
