import os
import yaml
import time
import requests
import base64
from pathlib import Path
from typing import Dict, Any, Optional, List
from PIL import Image
from dotenv import load_dotenv


class ConfigLoader:
    
    def __init__(self, env_path: str = None):
        if env_path is None:
            current_dir = Path(__file__).parent.parent.parent
            env_path = current_dir / ".env"
        self.env_path = env_path
        self._load_env()
    
    def _load_env(self):
        load_dotenv(self.env_path)
    
    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        return os.getenv(key, default)


class PromptLoader:
    
    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            current_dir = Path(__file__).parent.parent.parent
            prompts_dir = current_dir / "prompts"
        self.prompts_dir = Path(prompts_dir)
    
    def load_prompt(self, filename: str, prompt_key: str) -> str:
        file_path = self.prompts_dir / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as file:
            prompts = yaml.safe_load(file)
        
        if prompt_key not in prompts:
            raise KeyError(f"Prompt key '{prompt_key}' not found in {filename}")
        
        return prompts[prompt_key]


class LandingAIService:
    
    def __init__(self):
        self.config = ConfigLoader()
        self.prompt_loader = PromptLoader()
        self._initialize_client()
        self._load_prompts()
    
    def _initialize_client(self):
        self.api_key = self.config.get("LANDING_AI_API_KEY")
        if not self.api_key:
            raise ValueError("LANDING_AI_API_KEY not found in environment variables")
        
        self.base_url = "https://api.va.landing.ai/v1/ade"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        self.confidence_threshold = float(self.config.get("CONFIDENCE_THRESHOLD", "0.5"))
    
    def _load_prompts(self):
        self.defect_detection_prompt = self.prompt_loader.load_prompt(
            "document_processing.yaml", 
            "defect_detection_prompt"
        )
        self.classification_prompt = self.prompt_loader.load_prompt(
            "document_processing.yaml", 
            "classification_prompt"
        )
        self.visual_qa_prompt = self.prompt_loader.load_prompt(
            "document_processing.yaml", 
            "visual_qa_prompt"
        )
        self.validation_prompt = self.prompt_loader.load_prompt(
            "document_processing.yaml", 
            "validation_prompt"
        )
    
    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    async def process_document(
        self, 
        file_path: str = None,
        file_bytes: bytes = None,
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            if not file_path and not file_bytes:
                raise ValueError("Either file_path or file_bytes must be provided")
            
            files = {}
            if file_path:
                with open(file_path, 'rb') as f:
                    files = {'document': (Path(file_path).name, f, 'application/octet-stream')}
                    
                    response = requests.post(
                        f"{self.base_url}/parse",
                        headers=self.headers,
                        files=files,
                        timeout=30
                    )
            else:
                files = {'document': ('document', file_bytes, 'application/octet-stream')}
                response = requests.post(
                    f"{self.base_url}/parse",
                    headers=self.headers,
                    files=files,
                    timeout=30
                )
            
            if response.status_code != 200:
                raise Exception(f"API Error: {response.status_code} - {response.text}")
            
            result = response.json()
            
            extracted_data = {
                "text": result.get("markdown", ""),
                "tables": [],
                "key_value_pairs": {},
                "layout": result.get("chunks", []),
                "confidence": 0.95
            }
            
            for chunk in result.get("chunks", []):
                if chunk.get("type") == "table":
                    extracted_data["tables"].append(chunk)
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "message": "Document processed successfully",
                "extracted_data": extracted_data,
                "document_type": document_type or "Unknown",
                "processing_time": processing_time,
                "metadata": result.get("metadata", {})
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            return {
                "success": False,
                "message": f"Failed to process document: {str(e)}",
                "extracted_data": None,
                "processing_time": processing_time
            }
    
    async def validate_extraction(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            validation_results = {
                "has_text": bool(extracted_data.get("text")),
                "has_tables": bool(extracted_data.get("tables")),
                "has_key_value_pairs": bool(extracted_data.get("key_value_pairs")),
                "confidence_score": extracted_data.get("confidence", 0),
                "issues": []
            }
            
            if validation_results["confidence_score"] < self.confidence_threshold:
                validation_results["issues"].append(
                    f"Low confidence score: {validation_results['confidence_score']:.2f}"
                )
            
            if not validation_results["has_text"]:
                validation_results["issues"].append("No text extracted from document")
            
            validation_results["success"] = len(validation_results["issues"]) == 0
            
            return validation_results
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Validation failed: {str(e)}"
            }
