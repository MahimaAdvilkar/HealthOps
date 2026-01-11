from typing import Any, Dict, List

from ..agent_base import BaseAgent, AgentResult
from ..pipeline_states import PipelineState

class EligibilityVerifiedAgent(BaseAgent):
    name = "EligibilityVerifiedAgent"

    def run(self, context: Dict[str, Any]) -> AgentResult:
        normalized = context.get("normalized") or {}
        payer = normalized.get("payer") or {}

        issues: List[str] = []
        if not payer.get("name"): issues.append("payer.name missing")
        if not payer.get("member_id"): issues.append("payer.member_id missing")

        success = len(issues) == 0
        data = {
            "state": PipelineState.AUTH_PENDING.value if success else PipelineState.ELIGIBILITY_VERIFIED.value,
            "decisions": {"eligibility_verified": success},
            "normalized_patch": ({"eligibility": {"status": "verified"}} if success else {}),
            "actions_add": ([] if success else [{
                "type": "ELIGIBILITY_VERIFY",
                "owner": "Ops",
                "missing": issues
            }])
        }
        return AgentResult(name=self.name, success=success, data=data, issues=(issues or None))
