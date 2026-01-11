from __future__ import annotations

from typing import Dict, Any
from ..agent_base import BaseAgent, AgentResult


class NormalizedSummaryAgent(BaseAgent):
    name = "NormalizedSummaryAgent"

    def _norm_key(self, k: str) -> str | None:
        kl = k.strip().lower()
        mapping = {
              "referral id": "referral_id",
              "patient name": "patient_name",
              "date of birth": "date_of_birth",
              "payer": "payer",
              "payer name": "payer",
              "plan type": "plan_type",
              "authorization status": "authorization_status",
              "authorization number": "authorization_number",
              "authorization required": "authorization_required",
              "authorization start date": "authorization_start_date",
              "authorization end date": "authorization_end_date",
              "authorized units": "authorized_units",
              "units used": "units_used",
              "units delivered": "units_delivered",
              "unit type": "unit_type",
              "service category": "service_category",
              "procedure": "procedure",
              "date of service": "date_of_service",
              "ready to bill": "ready_to_bill",
              "billing hold reason": "billing_hold_reason",
              "facility": "facility",
              "city": "city",
              "technician name": "technician_name",
              "signed date": "signed_date",
              "issued date": "issued_date",
              "issued by": "issued_by",
              # New keys for member id variants
              "member id": "member_id",
              "memberid": "member_id",
              "member-id": "member_id",
              "member number": "member_id",
              "subscriber id": "member_id",
              # Assessment variants
              "assessment date": "assessment_date",
              "evaluation date": "assessment_date",
              "assessment status": "assessment_status",
              "evaluation status": "assessment_status",
              "assessment completed": "assessment_completed",
              "evaluation completed": "assessment_completed",
        }
        return mapping.get(kl)

    def run(self, context: Dict[str, Any]) -> AgentResult:
        text = context.get("extracted_text") or ""
        referral_id = context.get("referral_id") or ""
        if not text:
            return AgentResult(
                name=self.name,
                success=False,
                data={},
                issues=["Missing extracted_text in context"],
            )

        by_key: Dict[str, str] = {}
        for line in text.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                nk = self._norm_key(key)
                if nk:
                    by_key[nk] = val.strip()

        # ensure referral_id
        if referral_id:
            by_key.setdefault("referral_id", referral_id)

        return AgentResult(
            name=self.name,
            success=True,
            data={"normalized": by_key},
        )
