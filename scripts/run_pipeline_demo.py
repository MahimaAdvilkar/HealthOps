from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from src.services.agent_manager import AgentManager
from src.services.pipeline_utils import apply_agent_result
from src.services.pipeline_states import PipelineState

# Import your existing agents
from src.services.agents.document_extraction_agent import DocumentExtractionAgent
from src.services.agents.normalized_summary_agent import NormalizedSummaryAgent

# Import the new pipeline agents (create these next)
from src.services.agents.referral_received_agent import ReferralReceivedAgent
from src.services.agents.intake_complete_agent import IntakeCompleteAgent
from src.services.agents.assessment_complete_agent import AssessmentCompleteAgent
from src.services.agents.eligibility_verified_agent import EligibilityVerifiedAgent
from src.services.agents.auth_pending_agent import AuthPendingAgent
from src.services.agents.auth_approved_agent import AuthApprovedAgent
from src.services.agents.ready_to_schedule_agent import ReadyToScheduleAgent



def main():
    # 1) Build initial context
    context: Dict[str, Any] = {
        "case_id": "REF-1001",
        "state": PipelineState.REFERRAL_RECEIVED.value,
        "decisions": {},
        "actions": [],
        "normalized": {},
        "file_path": "data/documents/converted/packet_REF-1001.pdf",

        # put any file pointers your extraction agent needs:
        # "pdf_path": "converted/REF-1001.pdf",
    }

    # 2) Register agents in the order you want
    manager = AgentManager([
        DocumentExtractionAgent(),
        NormalizedSummaryAgent(),

        ReferralReceivedAgent(),
        IntakeCompleteAgent(),
        AssessmentCompleteAgent(),
        EligibilityVerifiedAgent(),
        AuthPendingAgent(),
        AuthApprovedAgent(),
        ReadyToScheduleAgent(),
    ])

    # 3) Run agents sequentially and apply updates immediately so downstream agents see new context
    results = []
    for agent in manager.agents:
        r = agent.run(context)
        print(f"{r.name}: success={r.success} issues={r.issues}")
        apply_agent_result(context, r.data)

        results.append(r)
        if not r.success:
            print("⛔ Stopping pipeline due to blocker.")
            break

    # 4) Print final state + actions
    print("\nFinal state:", context.get("state"))
    print("Decisions:", context.get("decisions"))
    print("Actions:", context.get("actions"))
    print("Normalized keys:", list((context.get("normalized") or {}).keys()))


if __name__ == "__main__":
    main()
