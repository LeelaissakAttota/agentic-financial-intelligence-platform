"""
Manager / Orchestrator Agent
TESTING PHASE STUB -- no production logic yet.

Responsibilities (see docs/ARCHITECTURE.md and docs/AGENT_PROMPTS.md
for the full contract):
  - Accept a validated input payload (see schema.py)
  - Call llm.claude_client with the system prompt from prompts.py
  - Parse/validate the model's JSON response against schema.py
  - Return a structured, schema-validated output object

TODO (Day 3 of docs/ROADMAP.md):
  - Implement run(input) -> output
  - Wire to llm/claude_client.py
  - Add unit test with mocked Claude response in tests/
"""

from .schema import AgentOutput  # noqa: F401
from .prompts import SYSTEM_PROMPT  # noqa: F401


class ManagerAgent:
    """Stub agent -- implement run() in Day 3 testing."""

    def run(self, payload: dict) -> dict:
        raise NotImplementedError("Implement during Day 3: Agent communication testing")
