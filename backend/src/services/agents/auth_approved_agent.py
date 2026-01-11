from typing import Any, Dict, List

from ..agent_base import BaseAgent, AgentResult
from ..pipeline_states import PipelineState

class AuthApprovedAgent(BaseAgent):
    name = "AuthApprovedAgent"

    def run(self, context: Dict[str, Any]) -> AgentResult:
        normalized = context.get("normalized") or {}
        auth = normalized.get("auth") or {}
        # Prefer normalized values from dataset
        normalized_status = str(normalized.get("authorization_status") or "").strip().lower()
        normalized_number = normalized.get("authorization_number")
        normalized_start = normalized.get("authorization_start_date")
        normalized_end = normalized.get("authorization_end_date")

        # If not required, skip.
        if auth.get("required") is False:
            return AgentResult(
                name=self.name,
                success=True,
                data={"state": PipelineState.READY_TO_SCHEDULE.value, "decisions": {"auth_approved": True}},
                issues=None
            )

        auth_number = normalized_number
        start = normalized_start
        end = normalized_end

        issues: List[str] = []
        if not auth_number: issues.append("auth_number missing")
        if not start: issues.append("auth_start_date missing")
        if not end: issues.append("auth_end_date missing")

        # If dataset says approved, honor it when required
        if auth.get("required") and normalized_status == "approved":
            success = True
            issues = []
        else:
            success = len(issues) == 0
        data = {
            "state": PipelineState.READY_TO_SCHEDULE.value if success else PipelineState.AUTH_APPROVED.value,
            "decisions": {"auth_approved": success},
            "normalized_patch": ({"auth": {"status": "approved", "auth_number": auth_number, "start_date": start, "end_date": end}} if success else {})
        }
        return AgentResult(name=self.name, success=success, data=data, issues=(issues or None))
