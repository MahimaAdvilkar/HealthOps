from datetime import date, datetime

class ReferralIntelligenceAgent:
    """
    Decides the next best action for a referral.
    This is the 'brain' of ReferralOS.
    """

    def evaluate(self, referral: dict) -> dict:
        today = date.today()

        # Default response
        result = {
            "agent_segment": "GREEN",
            "agent_next_action": "NO_ACTION",
            "agent_rationale": "Referral is progressing normally."
        }

        # Insurance inactive → HARD STOP
        if referral.get("insurance_active") == "N":
            return self._red(
                "HOLD",
                "Insurance inactive; block referral until eligibility resolved."
            )

        # Authorization logic
        if referral.get("auth_required") == "Y":
            if referral.get("auth_status") == "DENIED":
                return self._red(
                    "HOLD",
                    "Authorization denied; route to appeal or alternate plan."
                )

            if referral.get("auth_status") == "PENDING":
                return self._yellow(
                    "FOLLOW_UP_AUTH",
                    "Authorization pending; follow up with payer."
                )

        # Expiring authorization
        auth_end = referral.get("auth_end_date")
        if auth_end:
            days_left = (auth_end - today).days
            if days_left <= 3 and referral.get("schedule_status") != "SCHEDULED":
                return self._orange(
                    "ESCALATE",
                    "Authorization expiring soon and not scheduled; escalate immediately."
                )

        # Ready to schedule
        if (
            referral.get("auth_status") in ["APPROVED", "NOT_REQUIRED"]
            and referral.get("docs_complete") == "Y"
            and referral.get("schedule_status") == "NOT_SCHEDULED"
        ):
            return self._green(
                "SCHEDULE_NOW",
                "All checks passed; schedule service."
            )

        # Service completion → billing
        if (
            referral.get("schedule_status") == "COMPLETED"
            and referral.get("ready_to_bill") == "Y"
        ):
            return self._green(
                "SUBMIT_CLAIM",
                "Service completed and billing ready; submit claim."
            )

        return result

    # ---- Helpers ----

    def _green(self, action, rationale):
        return {
            "agent_segment": "GREEN",
            "agent_next_action": action,
            "agent_rationale": rationale
        }

    def _yellow(self, action, rationale):
        return {
            "agent_segment": "YELLOW",
            "agent_next_action": action,
            "agent_rationale": rationale
        }

    def _orange(self, action, rationale):
        return {
            "agent_segment": "ORANGE",
            "agent_next_action": action,
            "agent_rationale": rationale
        }

    def _red(self, action, rationale):
        return {
            "agent_segment": "RED",
            "agent_next_action": action,
            "agent_rationale": rationale
        }
