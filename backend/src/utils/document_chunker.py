import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
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


class DocumentChunker:
    
    def __init__(self):
        self.config = ConfigLoader()
        self.chunk_size = int(self.config.get("CHUNK_SIZE", "1000"))
        self.chunk_overlap = int(self.config.get("CHUNK_OVERLAP", "200"))
        self.section_markers = [
            r'^#+\s+',
            r'^\d+\.\s+',
            r'^[A-Z][A-Z\s]+:',
            r'^[IVX]+\.\s+',
            r'^\*\*.*\*\*$'
        ]
    
    def chunk_by_sections(
        self, 
        text: str,
        document_id: str = "unknown",
        preserve_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        sections = self._split_into_sections(text)
        
        chunks = []
        for idx, section in enumerate(sections):
            section_text = section['text'].strip()
            
            if len(section_text) > self.chunk_size:
                sub_chunks = self._split_by_size(section_text)
                for sub_idx, sub_chunk in enumerate(sub_chunks):
                    chunks.append({
                        "chunk_id": f"{document_id}_sec{idx}_chunk{sub_idx}",
                        "text": sub_chunk,
                        "section_title": section['title'],
                        "section_index": idx,
                        "chunk_index": sub_idx,
                        "chunk_type": "section_split",
                        "char_count": len(sub_chunk)
                    })
            else:
                chunks.append({
                    "chunk_id": f"{document_id}_sec{idx}",
                    "text": section_text,
                    "section_title": section['title'],
                    "section_index": idx,
                    "chunk_index": 0,
                    "chunk_type": "section",
                    "char_count": len(section_text)
                })
        
        return chunks
    
    def _split_into_sections(self, text: str) -> List[Dict[str, str]]:
        lines = text.split('\n')
        sections = []
        current_section = []
        current_title = "Introduction"
        
        for line in lines:
            is_section_header = False
            
            for pattern in self.section_markers:
                if re.match(pattern, line.strip()):
                    is_section_header = True
                    
                    if current_section:
                        sections.append({
                            "title": current_title,
                            "text": '\n'.join(current_section)
                        })
                    
                    current_title = line.strip()
                    current_section = []
                    break
            
            if not is_section_header:
                current_section.append(line)
        
        if current_section:
            sections.append({
                "title": current_title,
                "text": '\n'.join(current_section)
            })
        
        return sections
    
    def _split_by_size(self, text: str) -> List[str]:
        chunks = []
        sentences = self._split_into_sentences(text)
        
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                
                overlap_text = ' '.join(current_chunk[-2:]) if len(current_chunk) >= 2 else ''
                current_chunk = [overlap_text] if overlap_text else []
                current_length = len(overlap_text)
            
            current_chunk.append(sentence)
            current_length += sentence_length + 1
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        sentence_endings = r'[.!?]+[\s"]'
        sentences = re.split(sentence_endings, text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    
    def chunk_document_file(
        self, 
        file_path: str,
        document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")
        
        if document_id is None:
            document_id = file_path.stem
        
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        chunks = self.chunk_by_sections(text, document_id)
        
        for chunk in chunks:
            chunk['source_file'] = str(file_path.name)
            chunk['document_id'] = document_id
        
        return chunks
    
    def chunk_directory(
        self, 
        directory_path: str,
        file_pattern: str = "*.txt"
    ) -> Dict[str, List[Dict[str, Any]]]:
        directory_path = Path(directory_path)
        
        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        all_chunks = {}
        
        for file_path in directory_path.glob(file_pattern):
            document_id = file_path.stem
            chunks = self.chunk_document_file(file_path, document_id)
            all_chunks[document_id] = chunks
        
        return all_chunks
    
    def get_chunk_stats(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not chunks:
            return {
                "total_chunks": 0,
                "avg_chunk_size": 0,
                "min_chunk_size": 0,
                "max_chunk_size": 0,
                "total_chars": 0
            }
        
        chunk_sizes = [chunk['char_count'] for chunk in chunks]
        
        return {
            "total_chunks": len(chunks),
            "avg_chunk_size": sum(chunk_sizes) / len(chunk_sizes),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes),
            "total_chars": sum(chunk_sizes),
            "sections": len(set(chunk['section_title'] for chunk in chunks))
        }
