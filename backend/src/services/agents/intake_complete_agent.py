from typing import Any, Dict, List

from ..agent_base import BaseAgent, AgentResult
from ..pipeline_states import PipelineState

class IntakeCompleteAgent(BaseAgent):
    name = "IntakeCompleteAgent"

    def run(self, context: Dict[str, Any]) -> AgentResult:
        normalized = context.get("normalized") or {}
        patient = normalized.get("patient") or {}
        payer = normalized.get("payer") or {}
        referral = normalized.get("referral") or {}

        missing: List[str] = []
        has_patient_core = bool(patient.get("name")) and bool(patient.get("dob"))
        has_member = bool(payer.get("member_id"))
        if not has_patient_core and not has_member:
            missing.extend(["patient.name", "patient.dob", "payer.member_id"])
        if not payer.get("name"): missing.append("payer.name")
        if not referral.get("requested_service"): missing.append("referral.requested_service")

        success = len(missing) == 0
        data = {
            "state": PipelineState.ASSESSMENT_COMPLETE.value if success else PipelineState.INTAKE_COMPLETE.value,
            "decisions": {"intake_complete": success},
            "actions_add": ([] if success else [{
                "type": "MISSING_INFO",
                "owner": "Intake",
                "missing": missing
            }]),
            "missing": missing
        }
        return AgentResult(name=self.name, success=success, data=data, issues=(missing or None))
