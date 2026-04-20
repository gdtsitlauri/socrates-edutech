from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from random import Random
from statistics import fmean

from .models import CausalGap, ConceptNode, StudentProfile


@dataclass(frozen=True)
class InstrumentedEstimate:
    concept_id: str
    treatment_effect: float
    instrument_strength: float
    reduced_form_effect: float
    sample_size: int


def _bounded(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _collect_dependencies(
    concept_id: str,
    graph: dict[str, ConceptNode],
    collected: set[str] | None = None,
) -> set[str]:
    collected = collected or set()
    for prereq in graph[concept_id].prerequisites:
        if prereq in collected:
            continue
        collected.add(prereq)
        _collect_dependencies(prereq, graph, collected)
    return collected


def _targets_blocked_by(
    concept_id: str,
    target_concepts: list[str],
    graph: dict[str, ConceptNode],
) -> list[str]:
    blocked = []
    for target in target_concepts:
        dependencies = _collect_dependencies(target, graph)
        if concept_id == target or concept_id in dependencies:
            blocked.append(target)
    return blocked


def _stable_seed(student: StudentProfile, concept_id: str, target_concepts: list[str]) -> int:
    token = f"{student.student_id}:{concept_id}:{','.join(sorted(target_concepts))}"
    digest = sha256(token.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _simulate_iv_observations(
    concept_id: str,
    graph: dict[str, ConceptNode],
    student: StudentProfile,
    target_concepts: list[str],
    mastery_threshold: float,
    cohort_size: int,
) -> list[tuple[int, float, float]]:
    node = graph[concept_id]
    mastery = student.concept_mastery.get(concept_id, 0.0)
    deficiency = max(0.0, mastery_threshold - mastery)
    blocked_targets = _targets_blocked_by(concept_id, target_concepts, graph)
    dependency_relevance = max(1, len(blocked_targets))
    downstream_reach = node.downstream_weight + 0.4 * len(_collect_dependencies(blocked_targets[0], graph)) if blocked_targets else node.downstream_weight

    rng = Random(_stable_seed(student, concept_id, target_concepts))
    observations: list[tuple[int, float, float]] = []
    for _ in range(cohort_size):
        instrument = 1 if rng.random() < 0.5 else 0
        compliance_noise = rng.uniform(-0.05, 0.05)
        latent_engagement = rng.uniform(0.2, 0.95)
        baseline_practice = 0.12 + 0.55 * deficiency + 0.12 * latent_engagement
        treatment = _bounded(
            baseline_practice
            + instrument * (0.22 + 0.12 * deficiency + 0.03 * dependency_relevance)
            + compliance_noise,
            0.01,
            0.99,
        )

        true_effect = 0.04 + 0.28 * deficiency + 0.03 * dependency_relevance + 0.02 * downstream_reach
        base_outcome = 0.25 + 0.35 * mastery + 0.08 * latent_engagement
        outcome = _bounded(base_outcome + true_effect * treatment + rng.uniform(-0.035, 0.035))
        observations.append((instrument, treatment, outcome))
    return observations


def estimate_instrumented_effect(observations: list[tuple[int, float, float]], concept_id: str) -> InstrumentedEstimate:
    encouraged = [item for item in observations if item[0] == 1]
    control = [item for item in observations if item[0] == 0]
    if not encouraged or not control:
        return InstrumentedEstimate(
            concept_id=concept_id,
            treatment_effect=0.0,
            instrument_strength=0.0,
            reduced_form_effect=0.0,
            sample_size=len(observations),
        )

    mean_treatment_encouraged = fmean(item[1] for item in encouraged)
    mean_treatment_control = fmean(item[1] for item in control)
    mean_outcome_encouraged = fmean(item[2] for item in encouraged)
    mean_outcome_control = fmean(item[2] for item in control)

    instrument_strength = mean_treatment_encouraged - mean_treatment_control
    reduced_form = mean_outcome_encouraged - mean_outcome_control
    treatment_effect = reduced_form / instrument_strength if abs(instrument_strength) > 1e-6 else 0.0
    return InstrumentedEstimate(
        concept_id=concept_id,
        treatment_effect=round(treatment_effect, 4),
        instrument_strength=round(instrument_strength, 4),
        reduced_form_effect=round(reduced_form, 4),
        sample_size=len(observations),
    )


def discover_causal_gaps(
    graph: dict[str, ConceptNode],
    student: StudentProfile,
    target_concepts: list[str],
    mastery_threshold: float = 0.72,
    cohort_size: int = 320,
) -> dict[str, CausalGap]:
    candidates: set[str] = set(target_concepts)
    for target in target_concepts:
        candidates.update(_collect_dependencies(target, graph))

    results: dict[str, CausalGap] = {}
    for concept_id in sorted(candidates):
        observations = _simulate_iv_observations(
            concept_id=concept_id,
            graph=graph,
            student=student,
            target_concepts=target_concepts,
            mastery_threshold=mastery_threshold,
            cohort_size=cohort_size,
        )
        estimate = estimate_instrumented_effect(observations, concept_id)
        node = graph[concept_id]
        mastery = round(student.concept_mastery.get(concept_id, 0.0), 4)
        blocked_targets = _targets_blocked_by(concept_id, target_concepts, graph)
        blocked_titles = ", ".join(graph[target].title for target in blocked_targets) if blocked_targets else node.title
        reason = f"Instrumented prerequisite practice in {node.title} improves {blocked_titles}"
        results[concept_id] = CausalGap(
            concept_id=concept_id,
            title=node.title,
            reason=reason,
            causal_effect=estimate.treatment_effect,
            instrument_strength=estimate.instrument_strength,
            mastery=mastery,
        )
    return results
