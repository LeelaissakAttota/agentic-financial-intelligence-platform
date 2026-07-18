"""
Cross-Agent Memory Module - Phase 5

Provides shared memory and knowledge sharing across all agents.
"""

from data.memory.cross_agent_memory import (
    MemoryType,
    MemorySource,
    MemoryScope,
    MemoryEntry,
    MemoryBackend,
    PostgresMemoryBackend,
    CrossAgentMemory,
    create_cross_agent_memory,
)

__all__ = [
    "MemoryType",
    "MemorySource",
    "MemoryScope",
    "MemoryEntry",
    "MemoryBackend",
    "PostgresMemoryBackend",
    "CrossAgentMemory",
    "create_cross_agent_memory",
]