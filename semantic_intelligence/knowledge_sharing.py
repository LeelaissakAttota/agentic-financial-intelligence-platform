"""
Knowledge Sharing - Cross-agent knowledge sharing and synthesis.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict

from .memory_retrieval import get_memory_retrieval, Memory, MemoryType, MemoryScope
from .embeddings import get_embedding_service
from .vector_store import get_vector_store

logger = logging.getLogger(__name__)


class SharingAction(str, Enum):
    """Types of knowledge sharing actions."""
    BROADCAST = "broadcast"          # Broadcast to all agents
    TARGETED = "targeted"            # Share with specific agent
    REQUEST = "request"              # Request knowledge from agent
    SYNTHESIZE = "synthesize"        # Synthesize from multiple sources
    VALIDATE = "validate"            # Validate knowledge with peers


@dataclass
class KnowledgePacket:
    """Packet of knowledge shared between agents."""
    id: str
    source_agent: str
    target_agents: List[str]  # Empty = broadcast
    action: SharingAction
    memories: List[Memory]
    context: str = ""  # Why this is being shared
    priority: int = 50  # 0-100
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged_by: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SynthesisResult:
    """Result of knowledge synthesis."""
    query: str
    source_agents: List[str]
    synthesized_memories: List[Memory]
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    consensus_level: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)


class KnowledgeSharing:
    """
    Facilitates cross-agent knowledge sharing and synthesis.
    Enables agents to share memories, request information, and build collective intelligence.
    """
    
    def __init__(self):
        self.memory_retrieval = get_memory_retrieval()
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store()
        
        self._knowledge_queue: asyncio.Queue = asyncio.Queue()
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._agent_subscriptions: Dict[str, Set[str]] = defaultdict(set)  # agent -> topics
        self._knowledge_history: List[KnowledgePacket] = []
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize knowledge sharing."""
        await self.memory_retrieval.initialize()
        self._running = True
        self._processor_task = asyncio.create_task(self._process_queue())
        logger.info("Knowledge sharing initialized")
    
    async def stop(self) -> None:
        """Stop knowledge sharing."""
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        logger.info("Knowledge sharing stopped")
    
    def subscribe_agent(self, agent_id: str, topics: List[str]) -> None:
        """Subscribe agent to knowledge topics."""
        self._agent_subscriptions[agent_id].update(topics)
        logger.info(f"Agent {agent_id} subscribed to topics: {topics}")
    
    def unsubscribe_agent(self, agent_id: str, topics: List[str]) -> None:
        """Unsubscribe agent from topics."""
        for topic in topics:
            self._agent_subscriptions[agent_id].discard(topic)
    
    async def share_knowledge(
        self,
        source_agent: str,
        memories: List[Memory],
        target_agents: Optional[List[str]] = None,
        action: SharingAction = SharingAction.BROADCAST,
        context: str = "",
        priority: int = 50
    ) -> str:
        """Share knowledge with other agents."""
        packet = KnowledgePacket(
            id=f"kp_{datetime.utcnow().timestamp()}_{source_agent}",
            source_agent=source_agent,
            target_agents=target_agents or [],
            action=action,
            memories=memories,
            context=context,
            priority=priority,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        await self._knowledge_queue.put(packet)
        self._knowledge_history.append(packet)
        
        # Trim history
        if len(self._knowledge_history) > 10000:
            self._knowledge_history = self._knowledge_history[-5000:]
        
        logger.info(f"Knowledge packet queued from {source_agent} ({action.value})")
        return packet.id
    
    async def request_knowledge(
        self,
        requester: str,
        query: str,
        target_agents: Optional[List[str]] = None,
        timeout: float = 30.0
    ) -> List[Memory]:
        """Request knowledge from other agents."""
        request_id = f"req_{datetime.utcnow().timestamp()}_{requester}"
        future = asyncio.Future()
        self._pending_requests[request_id] = future
        
        # Create request packet
        packet = KnowledgePacket(
            id=request_id,
            source_agent=requester,
            target_agents=target_agents or [],
            action=SharingAction.REQUEST,
            memories=[],  # Will be filled by responders
            context=query,
            priority=80
        )
        
        await self._knowledge_queue.put(packet)
        
        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Knowledge request {request_id} timed out")
            return []
        finally:
            self._pending_requests.pop(request_id, None)
    
    async def _process_queue(self) -> None:
        """Process knowledge sharing queue."""
        while self._running:
            try:
                packet = await asyncio.wait_for(
                    self._knowledge_queue.get(),
                    timeout=1.0
                )
                
                await self._route_packet(packet)
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Knowledge queue processing error: {e}")
    
    async def _route_packet(self, packet: KnowledgePacket) -> None:
        """Route knowledge packet to target agents."""
        if packet.action == SharingAction.REQUEST:
            # Notify subscribed agents about request
            for agent_id, topics in self._agent_subscriptions.items():
                if agent_id == packet.source_agent:
                    continue
                
                # Check if agent subscribes to relevant topics
                query_terms = set(packet.context.lower().split())
                if any(term in " ".join(topics).lower() for term in query_terms):
                    # Agent might have relevant knowledge
                    # In real implementation, would send notification to agent
                    pass
        
        elif packet.action in [SharingAction.BROADCAST, SharingAction.TARGETED]:
            # Store memories for target agents
            for memory in packet.memories:
                # Add source tracking
                memory.metadata["shared_from"] = packet.source_agent
                memory.metadata["share_context"] = packet.context
                memory.metadata["share_timestamp"] = packet.created_at.isoformat()
            
            # Store in shared memory (accessible by all)
            for memory in packet.memories:
                memory.scope = MemoryScope.GLOBAL
                await self.memory_retrieval.store_memory(memory)
        
        # Check for pending requests this might satisfy
        if packet.action != SharingAction.REQUEST and packet.id in self._pending_requests:
            future = self._pending_requests.pop(packet.id)
            if not future.done():
                future.set_result(packet.memories)
    
    async def synthesize_knowledge(
        self,
        query: str,
        agent_ids: List[str],
        memory_types: Optional[List[MemoryType]] = None,
        min_confidence: float = 0.5
    ) -> SynthesisResult:
        """Synthesize knowledge from multiple agents."""
        all_memories = []
        source_agents = set()
        
        # Retrieve memories from each agent
        for agent_id in agent_ids:
            memories = await self.memory_retrieval.get_memories_by_agent(
                agent_id,
                scopes=[MemoryScope.GLOBAL, MemoryScope.AGENT, MemoryScope.COMPANY],
                limit=50
            )
            
            # Filter by type and confidence
            if memory_types:
                memories = [m for m in memories if m.type in memory_types]
            memories = [m for m in memories if m.confidence >= min_confidence]
            
            for mem in memories:
                mem.metadata["synthesis_source_agent"] = agent_id
                all_memories.append(mem)
                source_agents.add(agent_id)
        
        # Detect conflicts
        conflicts = self._detect_conflicts(all_memories)
        
        # Cluster similar memories
        clusters = self._cluster_memories(all_memories)
        
        # Create synthesized memories from clusters
        synthesized = []
        for cluster in clusters:
            if len(cluster) >= 2:  # At least 2 sources agree
                synth_memory = self._synthesize_cluster(cluster, query)
                if synth_memory:
                    synthesized.append(synth_memory)
        
        # Calculate confidence and consensus
        consensus = len(synthesized) / max(len(clusters), 1) if clusters else 0
        confidence = sum(m.confidence for m in synthesized) / max(len(synthesized), 1) if synthesized else 0
        
        return SynthesisResult(
            query=query,
            source_agents=list(source_agents),
            synthesized_memories=synthesized,
            conflicts=conflicts,
            confidence=confidence,
            consensus_level=consensus
        )
    
    def _detect_conflicts(self, memories: List[Memory]) -> List[Dict[str, Any]]:
        """Detect conflicting memories."""
        conflicts = []
        
        # Group by entity and type
        groups = defaultdict(list)
        for mem in memories:
            for entity in mem.related_entities:
                groups[(entity, mem.type)].append(mem)
        
        for (entity, mem_type), mems in groups.items():
            if len(mems) < 2:
                continue
            
            # Check for contradictions in content
            for i, mem1 in enumerate(mems):
                for mem2 in mems[i+1:]:
                    # Simple contradiction detection: opposite sentiment/confidence
                    if self._are_contradictory(mem1, mem2):
                        conflicts.append({
                            "entity": entity,
                            "type": mem_type.value,
                            "memory_1": {
                                "id": mem1.id,
                                "agent": mem1.metadata.get("synthesis_source_agent"),
                                "summary": mem1.summary,
                                "confidence": mem1.confidence
                            },
                            "memory_2": {
                                "id": mem2.id,
                                "agent": mem2.metadata.get("synthesis_source_agent"),
                                "summary": mem2.summary,
                                "confidence": mem2.confidence
                            },
                            "severity": "high" if abs(mem1.confidence - mem2.confidence) > 0.5 else "medium"
                        })
        
        return conflicts
    
    def _are_contradictory(self, mem1: Memory, mem2: Memory) -> bool:
        """Check if two memories are contradictory."""
        # Check for explicit contradictions in tags or content
        contradiction_indicators = [
            ("bullish", "bearish"),
            ("positive", "negative"),
            ("buy", "sell"),
            ("upgrade", "downgrade"),
            ("increase", "decrease"),
            ("growth", "decline"),
        ]
        
        content1 = (mem1.content + " " + " ".join(mem1.tags)).lower()
        content2 = (mem2.content + " " + " ".join(mem2.tags)).lower()
        
        for pos, neg in contradiction_indicators:
            if pos in content1 and neg in content2:
                return True
            if neg in content1 and pos in content2:
                return True
        
        # Check confidence divergence
        if abs(mem1.confidence - mem2.confidence) > 0.7:
            return True
        
        return False
    
    def _cluster_memories(self, memories: List[Memory]) -> List[List[Memory]]:
        """Cluster similar memories together."""
        if not memories:
            return []
        
        # Simple clustering by related entities
        clusters = defaultdict(list)
        for mem in memories:
            key = tuple(sorted(mem.related_entities)) if mem.related_entities else ("general",)
            clusters[key].append(mem)
        
        return list(clusters.values())
    
    def _synthesize_cluster(self, cluster: List[Memory], query: str) -> Optional[Memory]:
        """Synthesize a cluster of memories into a single memory."""
        if not cluster:
            return None
        
        # Weight by confidence
        total_confidence = sum(m.confidence for m in cluster)
        if total_confidence == 0:
            return None
        
        # Create weighted summary
        weighted_content = []
        for mem in cluster:
            weight = mem.confidence / total_confidence
            weighted_content.append(f"[{mem.metadata.get('synthesis_source_agent', 'unknown')}]: {mem.content}")
        
        # Aggregate metadata
        avg_confidence = sum(m.confidence for m in cluster) / len(cluster)
        avg_importance = sum(m.importance for m in cluster) / len(cluster)
        source_agents = list(set(m.metadata.get("synthesis_source_agent", "unknown") for m in cluster))
        
        synthesized = Memory(
            id=f"synth_{datetime.utcnow().timestamp()}",
            type=cluster[0].type,
            scope=MemoryScope.GLOBAL,
            content="\n".join(weighted_content),
            summary=f"Synthesized from {len(cluster)} sources: {', '.join(source_agents)}",
            embedding=None,  # Will be generated on store
            metadata={
                "synthesized": True,
                "source_count": len(cluster),
                "source_agents": source_agents,
                "original_query": query
            },
            importance=avg_importance,
            confidence=avg_confidence,
            related_entities=list(set().union(*[set(m.related_entities) for m in cluster])),
            tags=["synthesized", "consensus"] + cluster[0].tags
        )
        
        return synthesized
    
    async def validate_knowledge(
        self,
        memory: Memory,
        validators: List[str]
    ) -> Dict[str, Any]:
        """Request validation of knowledge from peer agents."""
        packet = KnowledgePacket(
            id=f"val_{datetime.utcnow().timestamp()}",
            source_agent="system",
            target_agents=validators,
            action=SharingAction.VALIDATE,
            memories=[memory],
            context=f"Validate: {memory.summary}",
            priority=90
        )
        
        await self._knowledge_queue.put(packet)
        
        # Wait for validations (simplified)
        await asyncio.sleep(5)
        
        return {
            "memory_id": memory.id,
            "validated": True,  # Would collect actual responses
            "validator_count": len(validators),
            "consensus": "pending"
        }
    
    def get_sharing_stats(self) -> Dict[str, Any]:
        """Get knowledge sharing statistics."""
        return {
            "packets_processed": len(self._knowledge_history),
            "pending_requests": len(self._pending_requests),
            "subscribed_agents": len(self._agent_subscriptions),
            "agent_subscriptions": {
                agent: list(topics) for agent, topics in self._agent_subscriptions.items()
            },
            "queue_size": self._knowledge_queue.qsize()
        }


# Global knowledge sharing instance
_knowledge_sharing: Optional[KnowledgeSharing] = None


def get_knowledge_sharing() -> KnowledgeSharing:
    """Get or create the global knowledge sharing instance."""
    global _knowledge_sharing
    if _knowledge_sharing is None:
        _knowledge_sharing = KnowledgeSharing()
    return _knowledge_sharing


async def close_knowledge_sharing() -> None:
    """Close the global knowledge sharing instance."""
    global _knowledge_sharing
    if _knowledge_sharing:
        await _knowledge_sharing.stop()
        _knowledge_sharing = None