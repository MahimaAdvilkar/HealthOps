import os
import yaml
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from PIL import Image
import io
import base64
from landingai.predict import Predictor
from landingai.pipeline.image_source import ImageSource
from dotenv import load_dotenv


class ConfigLoader:
    
    def __init__(self, env_path: str = ".env"):
        self.env_path = env_path
        self._load_env()
    
    def _load_env(self):
        load_dotenv(self.env_path)
    
    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        return os.getenv(key, default)


class PromptLoader:
    
    def __init__(self, prompts_dir: str = "prompts"):
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
        self._initialize_predictor()
        self._load_prompts()
    
    def _initialize_predictor(self):
        api_key = self.config.get("LANDING_AI_API_KEY")
        endpoint_id = self.config.get("LANDING_AI_ENDPOINT_ID")
        
        if not api_key:
            raise ValueError("LANDING_AI_API_KEY not found in environment variables")
        if not endpoint_id:
            raise ValueError("LANDING_AI_ENDPOINT_ID not found in environment variables")
        
        self.predictor = Predictor(
            endpoint_id=endpoint_id,
            api_key=api_key
        )
        
        self.confidence_threshold = float(self.config.get("CONFIDENCE_THRESHOLD", "0.5"))
        self.max_predictions = int(self.config.get("MAX_PREDICTIONS", "10"))
    
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
    
    def _decode_image(self, image_data: str) -> Image.Image:
        try:
            if image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]
            
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            return image
        except Exception as e:
            raise ValueError(f"Failed to decode image: {str(e)}")
    
    def _process_predictions(self, predictions: List[Dict]) -> List[Dict[str, Any]]:
        filtered_predictions = []
        
        for pred in predictions:
            confidence = pred.get('score', 0)
            if confidence >= self.confidence_threshold:
                filtered_predictions.append({
                    'label': pred.get('label', 'unknown'),
                    'confidence': confidence,
                    'bounding_box': pred.get('coordinates', {}),
                    'metadata': pred.get('metadata', {})
                })
        
        filtered_predictions.sort(key=lambda x: x['confidence'], reverse=True)
        return filtered_predictions[:self.max_predictions]
    
    async def process_image(
        self, 
        image_data: str, 
        image_type: Optional[str] = None,
        task_type: str = "defect_detection"
    ) -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            image = self._decode_image(image_data)
            
            predictions = self.predictor.predict(image)
            
            processed_predictions = self._process_predictions(predictions)
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "message": "Image processed successfully",
                "predictions": processed_predictions,
                "total_detections": len(processed_predictions),
                "image_type": image_type or "Unknown",
                "task_type": task_type,
                "processing_time": processing_time
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            return {
                "success": False,
                "message": f"Failed to process image: {str(e)}",
                "predictions": None,
                "total_detections": 0,
                "processing_time": processing_time
            }
    
    async def validate_predictions(self, predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            validation_results = {
                "total_predictions": len(predictions),
                "high_confidence": 0,
                "medium_confidence": 0,
                "low_confidence": 0,
                "issues": []
            }
            
            for pred in predictions:
                confidence = pred.get('confidence', 0)
                
                if confidence >= 0.8:
                    validation_results["high_confidence"] += 1
                elif confidence >= 0.5:
                    validation_results["medium_confidence"] += 1
                else:
                    validation_results["low_confidence"] += 1
                    validation_results["issues"].append(
                        f"Low confidence prediction: {pred.get('label')} ({confidence:.2f})"
                    )
                
                if not pred.get('bounding_box'):
                    validation_results["issues"].append(
                        f"Missing bounding box for: {pred.get('label')}"
                    )
            
            validation_results["success"] = len(validation_results["issues"]) == 0
            
            return validation_results
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Validation failed: {str(e)}"
            }
