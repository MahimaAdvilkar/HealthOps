from __future__ import annotations

from typing import Dict, Any
from ..agent_base import BaseAgent, AgentResult
from ..landingai_service import LandingAIService
import asyncio


class DocumentExtractionAgent(BaseAgent):
    name = "DocumentExtractionAgent"

    def __init__(self):
        self.service = LandingAIService()

    def run(self, context: Dict[str, Any]) -> AgentResult:
        file_path = context.get("file_path")
        file_bytes = context.get("file_bytes")
        doc_type = context.get("document_type")
        if not file_path and not file_bytes:
            return AgentResult(
                name=self.name,
                success=False,
                data={},
                issues=["Missing file_path or file_bytes in context"],
            )

        result = asyncio.run(
            self.service.process_document(
                file_path=file_path,
                file_bytes=file_bytes,
                document_type=doc_type,
            )
        )

        success = bool(result.get("success"))
        extracted = result.get("extracted_data") or {}
        table_count = len(extracted.get("tables") or [])

        return AgentResult(
            name=self.name,
            success=success,
            data={
                "document_type": result.get("document_type"),
                "processing_time": result.get("processing_time"),
                "table_count": table_count,
                "extracted_data": extracted,
            },
            issues=None if success else [result.get("message", "Unknown error")],
        )
