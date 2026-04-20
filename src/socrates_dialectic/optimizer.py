from __future__ import annotations

from collections import defaultdict

from .causal import discover_causal_gaps
from .irt import select_next_difficulty
from .models import CausalGap, ConceptNode, LearningPathResult, LearningStep, StudentProfile


def _expand_prerequisites(
    concept_id: str,
    graph: dict[str, ConceptNode],
    collected: set[str],
) -> None:
    if concept_id in collected:
        return
    collected.add(concept_id)
    for prereq in graph[concept_id].prerequisites:
        _expand_prerequisites(prereq, graph, collected)


def _descendant_weight(concept_id: str, graph: dict[str, ConceptNode]) -> float:
    children: dict[str, list[str]] = defaultdict(list)
    for node in graph.values():
        for prereq in node.prerequisites:
            children[prereq].append(node.concept_id)

    visited = set()
    stack = [concept_id]
    score = 0.0
    while stack:
        current = stack.pop()
        for child in children.get(current, []):
            if child in visited:
                continue
            visited.add(child)
            score += graph[child].downstream_weight
            stack.append(child)
    return score


def _topological_sort(candidates: set[str], graph: dict[str, ConceptNode]) -> list[str]:
    indegree = {concept: 0 for concept in candidates}
    children: dict[str, list[str]] = defaultdict(list)

    for concept in candidates:
        for prereq in graph[concept].prerequisites:
            if prereq in candidates:
                indegree[concept] += 1
                children[prereq].append(concept)

    ready = sorted(node for node, degree in indegree.items() if degree == 0)
    ordered: list[str] = []
    while ready:
        current = ready.pop(0)
        ordered.append(current)
        for child in sorted(children.get(current, [])):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                ready.sort()

    if len(ordered) != len(candidates):
        raise ValueError("graph contains a cycle or unresolved dependency")
    return ordered


def optimize_learning_path(
    graph: dict[str, ConceptNode],
    student: StudentProfile,
    target_concepts: list[str] | None = None,
    mastery_threshold: float = 0.72,
) -> LearningPathResult:
    """Produce a dependency-aware, causally ranked learning path for a student."""

    if target_concepts is None:
        target_concepts = [
            concept_id
            for concept_id, node in graph.items()
            if not node.prerequisites and student.concept_mastery.get(concept_id, 0.0) < mastery_threshold
        ]
        if not target_concepts:
            target_concepts = [
                concept_id
                for concept_id in graph
                if student.concept_mastery.get(concept_id, 0.0) < mastery_threshold
            ]

    closure: set[str] = set()
    for concept_id in target_concepts:
        _expand_prerequisites(concept_id, graph, closure)

    ordered_candidates = _topological_sort(closure, graph)
    steps: list[LearningStep] = []
    causal_gap_details = discover_causal_gaps(
        graph,
        student,
        target_concepts=list(target_concepts),
        mastery_threshold=mastery_threshold,
    )
    causal_gaps: list[CausalGap] = []

    for concept_id in ordered_candidates:
        node = graph[concept_id]
        causal_gap = causal_gap_details[concept_id]
        mastery = student.concept_mastery.get(concept_id, 0.0)
        deficiency = max(0.0, mastery_threshold - mastery)
        impact = node.downstream_weight + _descendant_weight(concept_id, graph)
        causal_weight = max(0.05, causal_gap.causal_effect) + max(0.05, causal_gap.instrument_strength)
        priority = round(
            (deficiency * max(1.0, impact) * (1.0 + causal_weight)) / max(5.0, node.estimated_minutes),
            4,
        )

        if deficiency > 0.0:
            if concept_id not in target_concepts:
                causal_gaps.append(causal_gap)
            steps.append(
                LearningStep(
                    concept_id=concept_id,
                    title=node.title,
                    priority=priority,
                    causal_reason=causal_gap.reason,
                    recommended_difficulty=select_next_difficulty(student.ability),
                    estimated_minutes=node.estimated_minutes,
                    causal_effect=causal_gap.causal_effect,
                    instrument_strength=causal_gap.instrument_strength,
                    mastery=round(mastery, 4),
                )
            )

    steps.sort(key=lambda step: (-step.priority, step.estimated_minutes, step.title))
    steps = _respect_dependencies(steps, graph)

    total_minutes = sum(step.estimated_minutes for step in steps) or 1.0
    estimated_gain = sum(step.priority for step in steps) * 60.0 / total_minutes

    return LearningPathResult(
        target_concepts=tuple(target_concepts),
        causal_gaps=tuple(sorted(causal_gaps, key=lambda item: (-item.causal_effect, item.title))),
        ordered_steps=tuple(steps),
        estimated_gain_per_hour=round(estimated_gain, 4),
    )


def _collect_dependencies(concept_id: str, graph: dict[str, ConceptNode]) -> set[str]:
    dependencies: set[str] = set()
    for prereq in graph[concept_id].prerequisites:
        dependencies.add(prereq)
        dependencies.update(_collect_dependencies(prereq, graph))
    return dependencies


def _respect_dependencies(
    steps: list[LearningStep],
    graph: dict[str, ConceptNode],
) -> list[LearningStep]:
    remaining = {step.concept_id: step for step in steps}
    ordered: list[LearningStep] = []

    while remaining:
        available = [
            step
            for step in remaining.values()
            if all(prereq not in remaining for prereq in graph[step.concept_id].prerequisites)
        ]
        available.sort(key=lambda step: (-step.priority, step.estimated_minutes, step.title))
        chosen = available[0]
        ordered.append(chosen)
        del remaining[chosen.concept_id]

    return ordered
