from __future__ import annotations

import csv
import random
from pathlib import Path

from .models import ConceptNode, StudentProfile
from .optimizer import optimize_learning_path


def build_demo_graph() -> dict[str, ConceptNode]:
    return {
        "numeracy": ConceptNode("numeracy", "Numeracy Foundations", (), 18.0, 1.2),
        "fractions": ConceptNode("fractions", "Fractions", ("numeracy",), 22.0, 1.5),
        "equations": ConceptNode("equations", "Linear Equations", ("fractions",), 24.0, 1.8),
        "functions": ConceptNode("functions", "Functions", ("equations",), 26.0, 2.0),
        "systems": ConceptNode("systems", "Systems of Equations", ("equations",), 28.0, 1.7),
        "statistics": ConceptNode("statistics", "Descriptive Statistics", ("numeracy",), 24.0, 0.8),
        "modeling": ConceptNode("modeling", "Mathematical Modeling", ("functions", "systems"), 30.0, 2.2),
    }


def _simulate_curriculum_effect(
    order: list[str],
    graph: dict[str, ConceptNode],
    base_mastery: dict[str, float],
    rng: random.Random,
) -> tuple[float, int]:
    mastery = dict(base_mastery)
    target = "modeling"
    target_path = {"numeracy", "fractions", "equations", "functions", "systems", "modeling"}
    for step_index, concept_id in enumerate(order, start=1):
        prereq_bonus = 0.0
        prereqs = graph[concept_id].prerequisites
        if prereqs:
            prereq_bonus = sum(mastery[prereq] for prereq in prereqs) / len(prereqs)
        relevance_bonus = 0.14 if concept_id in target_path else 0.03
        gain = 0.08 + relevance_bonus + 0.18 * prereq_bonus + rng.uniform(-0.015, 0.015)
        mastery[concept_id] = min(0.99, mastery.get(concept_id, 0.0) + gain)

        for node in graph.values():
            if concept_id in node.prerequisites:
                mastery[node.concept_id] = min(
                    0.99,
                    mastery.get(node.concept_id, 0.0) + 0.03 * mastery[concept_id],
                )

        if mastery[target] >= 0.85:
            return mastery[target], step_index
    return mastery[target], len(order)


def run_dialectic_experiment(
    seeds: tuple[int, ...] = (7, 11, 19),
    cohort_size: int = 1000,
) -> list[dict[str, float | int | str]]:
    graph = build_demo_graph()
    fixed_order = ["numeracy", "statistics", "fractions", "equations", "functions", "systems", "modeling"]
    rows: list[dict[str, float | int | str]] = []

    for seed in seeds:
        rng = random.Random(seed)
        mastery_scores = {"dialectic": [], "fixed": [], "random": []}
        steps_to_mastery = {"dialectic": [], "fixed": [], "random": []}

        for student_id in range(cohort_size):
            ability = rng.uniform(-1.2, 1.2)
            base_mastery = {
                concept_id: max(0.08, min(0.75, 0.35 + ability * 0.12 + rng.uniform(-0.08, 0.08)))
                for concept_id in graph
            }
            student = StudentProfile(
                student_id=student_id,
                name=f"Student {student_id}",
                course_id=1,
                concept_mastery=base_mastery,
                recent_scores=[max(40.0, min(98.0, 66.0 + ability * 12.0 + rng.uniform(-5.0, 5.0)))],
                ability=ability,
            )

            dialectic_steps = [
                step.concept_id
                for step in optimize_learning_path(graph, student, target_concepts=["modeling"]).ordered_steps
            ]
            random_order = fixed_order[:]
            rng.shuffle(random_order)

            for strategy, order in (
                ("dialectic", dialectic_steps),
                ("fixed", fixed_order),
                ("random", random_order),
            ):
                mastery, steps = _simulate_curriculum_effect(order, graph, base_mastery, rng)
                mastery_scores[strategy].append(mastery)
                steps_to_mastery[strategy].append(steps)

        for strategy in ("dialectic", "fixed", "random"):
            average_mastery = sum(mastery_scores[strategy]) / len(mastery_scores[strategy])
            average_steps = sum(steps_to_mastery[strategy]) / len(steps_to_mastery[strategy])
            learning_efficiency = average_mastery / max(1.0, average_steps)
            rows.append(
                {
                    "seed": seed,
                    "strategy": strategy,
                    "average_target_mastery": round(average_mastery, 4),
                    "average_steps_to_mastery": round(average_steps, 4),
                    "learning_efficiency": round(learning_efficiency, 4),
                }
            )
    return rows


def write_dialectic_results(output_path: Path) -> None:
    rows = run_dialectic_experiment()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "seed",
                "strategy",
                "average_target_mastery",
                "average_steps_to_mastery",
                "learning_efficiency",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
