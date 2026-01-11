from typing import Any, Dict, List

from ..agent_base import BaseAgent, AgentResult
from ..pipeline_states import PipelineState

class ReadyToScheduleAgent(BaseAgent):
    name = "ReadyToScheduleAgent"

    def run(self, context: Dict[str, Any]) -> AgentResult:
        normalized = context.get("normalized") or {}
        patient = normalized.get("patient") or {}
        eligibility = normalized.get("eligibility") or {}
        auth = normalized.get("auth") or {}

        issues: List[str] = []
        if not patient.get("phone") and not patient.get("address"):
            issues.append("Need patient phone or address")
        if eligibility.get("status") != "verified":
            issues.append("Eligibility not verified")
        if auth.get("required") and auth.get("status") != "approved":
            issues.append("Auth required but not approved")

        success = len(issues) == 0
        data = {
            "state": PipelineState.READY_TO_SCHEDULE.value,  # next states come later (caregiver matched, etc.)
            "decisions": {"ready_to_schedule": success},
            "actions_add": ([] if success else [{"type": "SCHEDULING_BLOCKER", "owner": "Scheduler", "blockers": issues}])
        }
        return AgentResult(name=self.name, success=success, data=data, issues=(issues or None))
