from typing import Any, Dict, List

from ..agent_base import BaseAgent, AgentResult
from ..pipeline_states import PipelineState

AUTH_REQUIRED_SERVICES = {"ECM", "Community Support", "CS"}

class AuthPendingAgent(BaseAgent):
    name = "AuthPendingAgent"

    def run(self, context: Dict[str, Any]) -> AgentResult:
        normalized = context.get("normalized") or {}
        referral = normalized.get("referral") or {}
        service = (referral.get("requested_service") or "").strip()
        # Prefer explicit flag from normalized if provided
        auth_required_flag = str(normalized.get("authorization_required") or "").strip().lower()

        issues: List[str] = []
        if not service:
            issues.append("referral.requested_service missing")

        if issues:
            return AgentResult(
                name=self.name,
                success=False,
                data={"state": PipelineState.AUTH_PENDING.value, "decisions": {"auth_planned": False}},
                issues=issues
            )

        if auth_required_flag in ("y", "yes", "true", "1"):
            auth_required = True
        elif auth_required_flag in ("n", "no", "false", "0"):
            auth_required = False
        else:
            auth_required = service in AUTH_REQUIRED_SERVICES
        actions_add = []
        if auth_required:
            actions_add.append({"type": "SUBMIT_AUTH", "owner": "Auth Team", "service": service})

        data = {
            "state": PipelineState.AUTH_APPROVED.value,  # next step checks approval
            "decisions": {"auth_required": auth_required, "auth_planned": True},
            "normalized_patch": {"auth": {"required": auth_required, "status": "pending" if auth_required else "not_required"}},
            "actions_add": actions_add
        }
        return AgentResult(name=self.name, success=True, data=data, issues=None)
