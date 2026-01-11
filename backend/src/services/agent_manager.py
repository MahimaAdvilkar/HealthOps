from __future__ import annotations

from typing import List, Dict, Any
from .agent_base import BaseAgent, AgentResult


class AgentManager:
    """Simple registry to orchestrate multiple agents."""

    def __init__(self, agents: List[BaseAgent] | None = None):
        self.agents: List[BaseAgent] = agents or []

    def register(self, agent: BaseAgent) -> None:
        self.agents.append(agent)

    def run_all(self, context: Dict[str, Any]) -> List[AgentResult]:
        results: List[AgentResult] = []
        for agent in self.agents:
            try:
                res = agent.run(context)
            except Exception as e:
                res = AgentResult(
                    name=getattr(agent, "name", agent.__class__.__name__),
                    success=False,
                    data={},
                    issues=[str(e)],
                )
            results.append(res)
        return results
