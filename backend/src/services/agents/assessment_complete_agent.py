from typing import Any, Dict, List

from ..agent_base import BaseAgent, AgentResult
from ..pipeline_states import PipelineState

class AssessmentCompleteAgent(BaseAgent):
    name = "AssessmentCompleteAgent"

    def run(self, context: Dict[str, Any]) -> AgentResult:
        normalized = context.get("normalized") or {}
        assessment = normalized.get("assessment") or {}

        assessment_done = assessment.get("status") == "complete" or bool(assessment.get("date"))

        issues: List[str] = []
        if not assessment_done:
            issues.append("Assessment not confirmed (need assessment.date or assessment.status=complete)")

        success = len(issues) == 0
        data = {
            "state": PipelineState.ELIGIBILITY_VERIFIED.value if success else PipelineState.ASSESSMENT_COMPLETE.value,
            "decisions": {"assessment_complete": success},
        }
        return AgentResult(name=self.name, success=success, data=data, issues=(issues or None))
