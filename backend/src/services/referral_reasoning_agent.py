from typing import Dict

class ReferralReasoningAgent:
    """
    Adds human-like reasoning on top of deterministic decisions.
    This is where LLMs live.
    """

    def explain(self, referral: Dict, decision: Dict) -> Dict:
        """
        Inputs:
        - referral: full referral record
        - decision: output from ReferralIntelligenceAgent

        Output:
        - explanation
        - risk_summary
        - ops_recommendation
        """

        explanation = f"""
        This referral is currently classified as {decision['agent_segment']}.
        The recommended action is {decision['agent_next_action']}.
        Reason: {decision['agent_rationale']}
        """

        risk_summary = self._summarize_risk(referral, decision)
        ops_recommendation = self._recommend_ops_action(referral, decision)

        return {
            "llm_explanation": explanation.strip(),
            "risk_summary": risk_summary,
            "ops_recommendation": ops_recommendation
        }

    def _summarize_risk(self, referral, decision):
        if decision["agent_segment"] == "RED":
            return "High risk of revenue loss or compliance failure."
        if decision["agent_segment"] == "ORANGE":
            return "Time-sensitive risk; immediate action required."
        if decision["agent_segment"] == "YELLOW":
            return "Moderate risk; requires follow-up."
        return "Low operational risk."

    def _recommend_ops_action(self, referral, decision):
        action = decision["agent_next_action"]

        if action == "ESCALATE":
            return "Escalate to supervisor and prioritize scheduling within 24 hours."
        if action == "FOLLOW_UP_AUTH":
            return "Contact payer and prepare contingency schedule."
        if action == "REQUEST_DOCS":
            return "Notify intake team to collect missing documentation."
        if action == "HOLD":
            return "Pause workflow until blocking issue resolved."
        if action == "SCHEDULE_NOW":
            return "Proceed with caregiver pairing and scheduling."
        return "Monitor referral."
