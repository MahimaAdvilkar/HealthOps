import os
import yaml
import json
import pickle
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
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


class FAISSService:
    
    def __init__(self):
        self.config = ConfigLoader()
        self.prompt_loader = PromptLoader()
        self._initialize_faiss()
        self._load_prompts()
    
    def _initialize_faiss(self):
        self.embedding_model_name = self.config.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.index_path = Path(self.config.get("FAISS_INDEX_PATH", "data/compliance/faiss_index"))
        self.metadata_path = Path(self.config.get("FAISS_METADATA_PATH", "data/compliance/metadata.pkl"))
        self.dimension = int(self.config.get("EMBEDDING_DIMENSION", "384"))
        self.top_k = int(self.config.get("FAISS_TOP_K", "5"))
        
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"Loading embedding model: {self.embedding_model_name}")
        self.model = SentenceTransformer(self.embedding_model_name)
        
        if self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            print(f"Loaded existing FAISS index with {self.index.ntotal} vectors")
        else:
            self.index = faiss.IndexFlatL2(self.dimension)
            print(f"Created new FAISS index with dimension {self.dimension}")
        
        if self.metadata_path.exists():
            with open(self.metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            print(f"Loaded metadata for {len(self.metadata)} documents")
        else:
            self.metadata = []
            print("Initialized empty metadata store")
    
    def _load_prompts(self):
        self.indexing_prompt = self.prompt_loader.load_prompt(
            "compliance_retrieval.yaml", 
            "indexing_prompt"
        )
        self.search_prompt = self.prompt_loader.load_prompt(
            "compliance_retrieval.yaml", 
            "search_prompt"
        )
        self.relevance_prompt = self.prompt_loader.load_prompt(
            "compliance_retrieval.yaml", 
            "relevance_prompt"
        )
    
    def _save_index(self):
        faiss.write_index(self.index, str(self.index_path))
        with open(self.metadata_path, 'wb') as f:
            pickle.dump(self.metadata, f)
        print(f"Saved FAISS index and metadata")
    
    def add_document(
        self, 
        document_id: str,
        text: str,
        document_type: str = "compliance",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        try:
            embedding = self.model.encode([text])[0]
            
            self.index.add(np.array([embedding], dtype=np.float32))
            
            doc_metadata = {
                "id": document_id,
                "text": text,
                "document_type": document_type,
                "embedding_index": self.index.ntotal - 1,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            self.metadata.append(doc_metadata)
            
            self._save_index()
            
            return {
                "success": True,
                "message": f"Document {document_id} added successfully",
                "document_id": document_id,
                "index_position": self.index.ntotal - 1,
                "total_documents": self.index.ntotal
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to add document: {str(e)}"
            }
    
    def add_documents_batch(
        self, 
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        try:
            texts = [doc["text"] for doc in documents]
            embeddings = self.model.encode(texts)
            
            self.index.add(np.array(embeddings, dtype=np.float32))
            
            start_index = self.index.ntotal - len(documents)
            for idx, doc in enumerate(documents):
                doc_metadata = {
                    "id": doc.get("id", f"doc_{start_index + idx}"),
                    "text": doc["text"],
                    "document_type": doc.get("document_type", "compliance"),
                    "embedding_index": start_index + idx,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": doc.get("metadata", {})
                }
                self.metadata.append(doc_metadata)
            
            self._save_index()
            
            return {
                "success": True,
                "message": f"Added {len(documents)} documents successfully",
                "documents_added": len(documents),
                "total_documents": self.index.ntotal
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to add documents: {str(e)}"
            }
    
    def search(
        self, 
        query: str,
        top_k: Optional[int] = None,
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            if top_k is None:
                top_k = self.top_k
            
            query_embedding = self.model.encode([query])[0]
            
            distances, indices = self.index.search(
                np.array([query_embedding], dtype=np.float32), 
                min(top_k * 2, self.index.ntotal)
            )
            
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < len(self.metadata):
                    doc = self.metadata[idx]
                    
                    if document_type and doc.get("document_type") != document_type:
                        continue
                    
                    similarity_score = 1 / (1 + float(dist))
                    
                    results.append({
                        "document_id": doc["id"],
                        "text": doc["text"],
                        "document_type": doc["document_type"],
                        "similarity_score": similarity_score,
                        "distance": float(dist),
                        "metadata": doc.get("metadata", {})
                    })
                    
                    if len(results) >= top_k:
                        break
            
            return {
                "success": True,
                "message": f"Found {len(results)} relevant documents",
                "query": query,
                "results": results,
                "total_searched": self.index.ntotal
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Search failed: {str(e)}",
                "query": query,
                "results": []
            }
    
    def delete_document(self, document_id: str) -> Dict[str, Any]:
        try:
            doc_index = None
            for idx, doc in enumerate(self.metadata):
                if doc["id"] == document_id:
                    doc_index = idx
                    break
            
            if doc_index is None:
                return {
                    "success": False,
                    "message": f"Document {document_id} not found"
                }
            
            del self.metadata[doc_index]
            
            self._rebuild_index()
            
            return {
                "success": True,
                "message": f"Document {document_id} deleted successfully",
                "total_documents": self.index.ntotal
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to delete document: {str(e)}"
            }
    
    def _rebuild_index(self):
        self.index = faiss.IndexFlatL2(self.dimension)
        
        if self.metadata:
            texts = [doc["text"] for doc in self.metadata]
            embeddings = self.model.encode(texts)
            self.index.add(np.array(embeddings, dtype=np.float32))
            
            for idx, doc in enumerate(self.metadata):
                doc["embedding_index"] = idx
        
        self._save_index()
    
    def get_stats(self) -> Dict[str, Any]:
        document_types = {}
        for doc in self.metadata:
            doc_type = doc.get("document_type", "unknown")
            document_types[doc_type] = document_types.get(doc_type, 0) + 1
        
        return {
            "total_documents": self.index.ntotal,
            "index_dimension": self.dimension,
            "embedding_model": self.embedding_model_name,
            "document_types": document_types,
            "index_path": str(self.index_path),
            "metadata_count": len(self.metadata)
        }
