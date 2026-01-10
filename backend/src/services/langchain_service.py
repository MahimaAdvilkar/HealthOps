import os
import yaml
import time
from pathlib import Path
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv


class ConfigLoader:
    
    def __init__(self, env_path: str = "config/env/.env"):
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


class LangChainService:
    
    def __init__(self):
        self.config = ConfigLoader()
        self.prompt_loader = PromptLoader()
        self._initialize_llm()
        self._load_prompts()
    
    def _initialize_llm(self):
        api_key = self.config.get("OPENAI_API_KEY")
        model_name = self.config.get("MODEL_NAME", "gpt-4")
        temperature = float(self.config.get("MODEL_TEMPERATURE", "0.7"))
        max_tokens = int(self.config.get("MAX_TOKENS", "2000"))
        
        self.llm = ChatOpenAI(
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    def _load_prompts(self):
        self.system_prompt = self.prompt_loader.load_prompt(
            "document_processing.yaml", 
            "system_prompt"
        )
        self.analysis_prompt = self.prompt_loader.load_prompt(
            "document_processing.yaml", 
            "document_analysis_prompt"
        )
        self.validation_prompt = self.prompt_loader.load_prompt(
            "document_processing.yaml", 
            "validation_prompt"
        )
    
    async def process_document(self, document_content: str, document_type: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            prompt_template = PromptTemplate(
                input_variables=["document_content"],
                template=self.analysis_prompt
            )
            
            chain = LLMChain(llm=self.llm, prompt=prompt_template)
            
            result = await chain.arun(document_content=document_content)
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "message": "Document processed successfully",
                "extracted_data": {
                    "analysis": result,
                    "document_type": document_type or "Unknown"
                },
                "processing_time": processing_time
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
            prompt_template = PromptTemplate(
                input_variables=["extracted_data"],
                template=self.validation_prompt
            )
            
            chain = LLMChain(llm=self.llm, prompt=prompt_template)
            result = await chain.arun(extracted_data=str(extracted_data))
            
            return {
                "success": True,
                "validation_result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Validation failed: {str(e)}"
            }
