from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConceptNode:
    concept_id: str
    title: str
    prerequisites: tuple[str, ...] = ()
    estimated_minutes: float = 20.0
    downstream_weight: float = 1.0


@dataclass
class StudentProfile:
    student_id: int
    name: str
    course_id: int
    learning_style: str = "blended"
    concept_mastery: dict[str, float] = field(default_factory=dict)
    recent_scores: list[float] = field(default_factory=list)
    ability: float = 0.0

    def average_score(self) -> float:
        if not self.recent_scores:
            return 0.0
        return sum(self.recent_scores) / len(self.recent_scores)


@dataclass(frozen=True)
class CausalGap:
    concept_id: str
    title: str
    reason: str
    causal_effect: float
    instrument_strength: float
    mastery: float


@dataclass(frozen=True)
class LearningStep:
    concept_id: str
    title: str
    priority: float
    causal_reason: str
    recommended_difficulty: str
    estimated_minutes: float
    causal_effect: float
    instrument_strength: float
    mastery: float


@dataclass(frozen=True)
class LearningPathResult:
    target_concepts: tuple[str, ...]
    causal_gaps: tuple[CausalGap, ...]
    ordered_steps: tuple[LearningStep, ...]
    estimated_gain_per_hour: float
