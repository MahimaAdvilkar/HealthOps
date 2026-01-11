from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from abc import ABC, abstractmethod


@dataclass
class AgentResult:
    name: str
    success: bool
    data: Dict[str, Any]
    issues: Optional[list[str]] = None


class BaseAgent(ABC):
    """Minimal base interface for HealthOps agents."""

    name: str = "BaseAgent"

    @abstractmethod
    def run(self, context: Dict[str, Any]) -> AgentResult:
        """Execute agent logic against provided context.

        Context is a flexible dict; agents document required keys.
        """
        raise NotImplementedError
