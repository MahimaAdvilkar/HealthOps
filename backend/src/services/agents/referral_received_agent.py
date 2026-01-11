from typing import Any, Dict, List

from ..agent_base import BaseAgent, AgentResult
from ..pipeline_states import PipelineState

class ReferralReceivedAgent(BaseAgent):
    name = "ReferralReceivedAgent"

    def run(self, context: Dict[str, Any]) -> AgentResult:
        extraction = context.get("extraction") or {}
        fields = (extraction.get("extraction") or {}).get("fields") or {}

        patient_name = fields.get("patient_name") or fields.get("name")
        dob = fields.get("dob") or fields.get("date_of_birth")
        member_id = fields.get("member_id") or fields.get("insurance_id")

        issues: List[str] = []
        if not ((patient_name and dob) or member_id):
            issues.append("Need patient_name+dob OR member_id to open case")

        success = len(issues) == 0
        data = {
            "state": PipelineState.INTAKE_COMPLETE.value if success else PipelineState.REFERRAL_RECEIVED.value,
            "decisions": {
                "referral_received": success,
            },
            "normalized_patch": {
                "patient": {"name": patient_name, "dob": dob},
                "payer": {"member_id": member_id},
            }
        }

        return AgentResult(name=self.name, success=success, data=data, issues=issues or None)
