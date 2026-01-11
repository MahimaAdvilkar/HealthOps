import os
import yaml
import time
import requests
import base64
import io
from pathlib import Path
from typing import Dict, Any, Optional, List
from PIL import Image
from dotenv import load_dotenv
from fpdf import FPDF


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
        self._load_extraction_rules()
    
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
    
    def _load_extraction_rules(self):
        """Load extraction rules from data/extraction_rules.yaml"""
        try:
            # Navigate to data folder from backend/src/services
            current_dir = Path(__file__).parent.parent.parent.parent
            rules_path = current_dir / "data" / "extraction_rules.yaml"
            
            if not rules_path.exists():
                print(f"Warning: Extraction rules file not found at {rules_path}")
                self.extraction_rules = {}
                return
            
            with open(rules_path, 'r', encoding='utf-8') as f:
                self.extraction_rules = yaml.safe_load(f)
            
            print(f"Loaded extraction rules from {rules_path}")
            print(f"Available document types: {list(self.extraction_rules.get('extraction_rules', {}).keys())}")
            
        except Exception as e:
            print(f"Error loading extraction rules: {e}")
            self.extraction_rules = {}
    
    def get_document_type_from_text(self, text: str) -> str:
        """
        Identify document type based on keywords from extraction rules
        """
        text_lower = text.lower()
        doc_types = self.extraction_rules.get('document_types', {})
        
        for doc_type, config in doc_types.items():
            keywords = config.get('keywords', [])
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return doc_type
        
        return "unknown"
    
    def get_extraction_fields(self, document_type: str) -> Dict[str, Any]:
        """
        Get extraction field definitions for a document type
        """
        rules = self.extraction_rules.get('extraction_rules', {})
        return rules.get(document_type, {}).get('required_fields', {})
    
    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def _sanitize_text(self, s: str) -> str:
        # Replace common unicode punctuation with ASCII for core fonts
        return (
            s.replace("\u2013", "-")
             .replace("\u2014", "-")
             .replace("\u2019", "'")
             .replace("\u2018", "'")
             .replace("\u201c", '"')
             .replace("\u201d", '"')
        )

    def _text_to_pdf_bytes(self, text: str) -> bytes:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        safe_text = self._sanitize_text(text)
        pdf.multi_cell(0, 10, safe_text)
        out = io.BytesIO()
        pdf.output(out)
        return out.getvalue()
    
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
                # If a text file is provided, convert to PDF first
                suffix = Path(file_path).suffix.lower()
                if suffix == ".txt":
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as tf:
                        text = tf.read()
                    pdf_bytes = self._text_to_pdf_bytes(text)
                    files = {'document': ('document.pdf', pdf_bytes, 'application/pdf')}
                else:
                    # Read to bytes to avoid closed file issues
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    # Use appropriate content type
                    content_type = 'application/pdf' if suffix == '.pdf' else 'application/octet-stream'
                    files = {'document': (Path(file_path).name, content, content_type)}

                response = requests.post(
                    f"{self.base_url}/parse",
                    headers=self.headers,
                    files=files,
                    timeout=30
                )
            else:
                # If bytes provided and not PDF, convert text to PDF
                is_pdf = bool(file_bytes) and file_bytes[:4] == b"%PDF"
                if not is_pdf:
                    try:
                        text = file_bytes.decode('utf-8', errors='ignore')
                        pdf_bytes = self._text_to_pdf_bytes(text)
                        files = {'document': ('document.pdf', pdf_bytes, 'application/pdf')}
                    except Exception:
                        files = {'document': ('document', file_bytes, 'application/octet-stream')}
                else:
                    files = {'document': ('document.pdf', file_bytes, 'application/pdf')}

                response = requests.post(
                    f"{self.base_url}/parse",
                    headers=self.headers,
                    files=files,
                    timeout=30
                )
            
            if response.status_code != 200:
                raise Exception(f"API Error: {response.status_code} - {response.text}")
            
            result = response.json()
            
            # Extract text content
            extracted_text = result.get("markdown", "")
            
            # Auto-detect document type if not provided
            if not document_type:
                document_type = self.get_document_type_from_text(extracted_text)
            
            # Get extraction rules for this document type
            extraction_fields = self.get_extraction_fields(document_type)
            
            extracted_data = {
                "text": extracted_text,
                "tables": [],
                "key_value_pairs": {},
                "layout": result.get("chunks", []),
                "confidence": 0.95,
                "document_type": document_type,
                "expected_fields": list(extraction_fields.keys()) if extraction_fields else [],
                "extraction_rules_applied": bool(extraction_fields)
            }
            
            for chunk in result.get("chunks", []):
                if chunk.get("type") == "table":
                    extracted_data["tables"].append(chunk)
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "message": "Document processed successfully",
                "extracted_data": extracted_data,
                "document_type": document_type,
                "processing_time": processing_time,
                "metadata": result.get("metadata", {}),
                "extraction_rules": {
                    "type": document_type,
                    "fields_to_extract": list(extraction_fields.keys()) if extraction_fields else [],
                    "rules_applied": bool(extraction_fields)
                }
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
            # Get document type and extraction rules
            document_type = extracted_data.get("document_type", "unknown")
            extraction_fields = self.get_extraction_fields(document_type)
            
            validation_results = {
                "has_text": bool(extracted_data.get("text")),
                "has_tables": bool(extracted_data.get("tables")),
                "has_key_value_pairs": bool(extracted_data.get("key_value_pairs")),
                "confidence_score": extracted_data.get("confidence", 0),
                "document_type": document_type,
                "expected_fields": list(extraction_fields.keys()) if extraction_fields else [],
                "issues": []
            }
            
            # Check confidence against rules threshold
            rules_threshold = self.extraction_rules.get('settings', {}).get('confidence_threshold', 0.75)
            if validation_results["confidence_score"] < rules_threshold:
                validation_results["issues"].append(
                    f"Low confidence score: {validation_results['confidence_score']:.2f} (threshold: {rules_threshold})"
                )
            
            if not validation_results["has_text"]:
                validation_results["issues"].append("No text extracted from document")
            
            # Check if required fields are present (basic keyword check)
            if extraction_fields and validation_results["has_text"]:
                text_lower = extracted_data.get("text", "").lower()
                missing_fields = []
                for field_name, field_config in extraction_fields.items():
                    # Simple check - look for field name in text
                    if field_name.replace("_", " ") not in text_lower:
                        missing_fields.append(field_name)
                
                if missing_fields:
                    validation_results["issues"].append(
                        f"Potentially missing fields: {', '.join(missing_fields[:5])}"
                    )
            
            validation_results["success"] = len(validation_results["issues"]) == 0
            
            return validation_results
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Validation failed: {str(e)}"
            }
