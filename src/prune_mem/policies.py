from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math

from .models import MemoryRecord, MemoryStatus, SourceLevel


@dataclass(slots=True)
class PolicyDecision:
    action: str
    reason: str


@dataclass(slots=True)
class PolicyConfig:
    min_importance: float = 0.55
    min_confidence: float = 0.7
    min_stability: float = 0.6
    implicit_min_evidence: int = 2
    stale_after_days: int = 30
    archive_after_days: int = 90
    max_recall_items: int = 8
    per_category_limit: int = 2
    token_budget: int = 900
    active_health_floor: float = 0.5
    archive_health_floor: float = 0.2
    dedupe_similarity_threshold: float = 0.78


def admission_decision(memory: MemoryRecord, config: PolicyConfig) -> PolicyDecision:
    if memory.source_level is SourceLevel.INFERRED:
        return PolicyDecision("reject", "inferred memories stay out of long-term storage by default")
    if memory.importance < config.min_importance:
        return PolicyDecision("reject", "importance below admission floor")
    if memory.confidence < config.min_confidence:
        return PolicyDecision("reject", "confidence below admission floor")
    if memory.source_level is SourceLevel.IMPLICIT and memory.evidence_count < config.implicit_min_evidence:
        return PolicyDecision("hold", "implicit memory needs repeated evidence")
    if memory.stability < config.min_stability and memory.slot_key:
        return PolicyDecision("hold", "slot memories need stronger stability")
    return PolicyDecision("accept", "memory passed admission gates")


def source_rank(source_level: SourceLevel) -> int:
    order = {
        SourceLevel.EXPLICIT: 3,
        SourceLevel.IMPLICIT: 2,
        SourceLevel.INFERRED: 1,
    }
    return order[source_level]


def health_score(memory: MemoryRecord, now: datetime, config: PolicyConfig) -> float:
    age_days = max(0.0, (now - memory.last_seen_at).total_seconds() / 86400)
    freshness = math.exp(-age_days / max(config.stale_after_days, 1))
    reinforcement = min(1.0, math.log1p(memory.evidence_count) / math.log(6))
    access = min(1.0, math.log1p(memory.access_count) / math.log(6))
    source_bonus = source_rank(memory.source_level) / 3
    base_quality = (
        memory.importance * 0.38
        + memory.confidence * 0.27
        + memory.stability * 0.2
        + source_bonus * 0.15
    )
    freshness_factor = 0.75 + 0.25 * freshness
    reinforcement_factor = 0.8 + 0.2 * reinforcement
    access_factor = 1.0 + 0.1 * access
    return round(base_quality * freshness_factor * reinforcement_factor * access_factor, 4)


def overwrite_decision(existing: MemoryRecord, incoming: MemoryRecord) -> PolicyDecision:
    if existing.slot_key != incoming.slot_key:
        return PolicyDecision("separate", "different slot keys")
    existing_strength = (
        existing.confidence + existing.importance + existing.stability + source_rank(existing.source_level) / 3
    )
    incoming_strength = (
        incoming.confidence + incoming.importance + incoming.stability + source_rank(incoming.source_level) / 3
    )
    if incoming.value == existing.value:
        return PolicyDecision("reinforce", "same slot value, reinforce existing memory")
    if incoming_strength > existing_strength + 0.2:
        return PolicyDecision("replace", "new evidence is materially stronger")
    if incoming.source_level is SourceLevel.EXPLICIT and existing.source_level is not SourceLevel.EXPLICIT:
        return PolicyDecision("replace", "explicit evidence outranks weaker prior source")
    return PolicyDecision("retain", "existing slot remains stronger for now")


def apply_decay(memory: MemoryRecord, now: datetime, config: PolicyConfig) -> PolicyDecision:
    age_days = max(0.0, (now - memory.last_seen_at).total_seconds() / 86400)
    health = health_score(memory, now, config)
    if memory.status in {MemoryStatus.REJECTED, MemoryStatus.ARCHIVED, MemoryStatus.RETIRED}:
        return PolicyDecision("noop", "memory is not eligible for decay changes")
    if age_days >= config.archive_after_days and health < config.archive_health_floor:
        return PolicyDecision("archive", "low-health memory exceeded archive horizon")
    if age_days >= config.stale_after_days and health < config.active_health_floor:
        return PolicyDecision("stale", "memory exceeded stale horizon with low health")
    if memory.status is MemoryStatus.STALE and health >= config.active_health_floor:
        return PolicyDecision("reactivate", "health recovered above stale floor")
    return PolicyDecision("keep", "memory health remains acceptable")


def retrieval_score(memory: MemoryRecord, query_tags: set[str], now: datetime, config: PolicyConfig) -> float:
    health = health_score(memory, now, config)
    tag_overlap = len(query_tags.intersection(memory.tags))
    relevance = min(1.0, 0.35 + 0.2 * tag_overlap)
    return round(
        relevance * 0.4 + health * 0.45 + min(1.0, memory.access_count / 5) * 0.15,
        4,
    )


def estimate_tokens(memory: MemoryRecord) -> int:
    text = " ".join([memory.summary, memory.value, " ".join(memory.tags)])
    return max(16, math.ceil(len(text) / 4))
