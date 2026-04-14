from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

from socrates_dialectic import (
    ReviewState,
    StudentProfile,
    bkt_update,
    build_demo_graph,
    build_learning_path_payload,
    discover_causal_gaps,
    estimate_theta_binary,
    irt_probability,
    multiply_matrices,
    optimize_learning_path,
    run_dialectic_experiment,
    sm2_review,
)


def test_bkt_update() -> None:
    prior = 0.35
    posterior_correct = bkt_update(prior, True)
    posterior_incorrect = bkt_update(prior, False)
    assert posterior_correct > prior
    assert posterior_incorrect < posterior_correct


def test_causal_learning_path() -> None:
    graph = build_demo_graph()
    student = StudentProfile(
        student_id=1,
        name="Ava",
        course_id=101,
        concept_mastery={
            "numeracy": 0.55,
            "fractions": 0.41,
            "equations": 0.38,
            "functions": 0.2,
            "systems": 0.25,
            "modeling": 0.12,
        },
        ability=-0.4,
    )

    path = optimize_learning_path(graph, student, target_concepts=["modeling"])
    ordered_ids = [step.concept_id for step in path.ordered_steps]
    assert ordered_ids[:3] == ["numeracy", "fractions", "equations"]
    assert "fractions" in {gap.concept_id for gap in path.causal_gaps}
    assert path.estimated_gain_per_hour > 0.0
    assert all(step.causal_effect > 0.0 for step in path.ordered_steps)
    assert all(step.instrument_strength > 0.0 for step in path.ordered_steps)


def test_causal_gap_discovery_uses_instrumented_effects() -> None:
    graph = build_demo_graph()
    student = StudentProfile(
        student_id=22,
        name="Niko",
        course_id=101,
        concept_mastery={
            "numeracy": 0.49,
            "fractions": 0.31,
            "equations": 0.27,
            "functions": 0.18,
            "systems": 0.21,
            "modeling": 0.11,
        },
        ability=-0.55,
    )

    gaps = discover_causal_gaps(graph, student, target_concepts=["modeling"])
    fractions_gap = gaps["fractions"]
    assert fractions_gap.causal_effect > 0.0
    assert fractions_gap.instrument_strength > 0.0
    assert "Functions" in gaps["equations"].reason or "Mathematical Modeling" in gaps["equations"].reason


def test_irt_calibration() -> None:
    theta_true = 0.75
    difficulties = [-1.0, -0.5, 0.0, 0.5, 1.0, 1.5]
    responses = [1 if irt_probability(theta_true, difficulty) >= 0.5 else 0 for difficulty in difficulties]
    estimate = estimate_theta_binary(responses, difficulties)
    assert abs(estimate - theta_true) < 0.5


def test_spaced_repetition() -> None:
    state = ReviewState(
        last_review=date(2026, 4, 1),
        next_review=date(2026, 4, 2),
        interval_days=1,
        ease_factor=2.5,
        repetitions=1,
    )
    second = sm2_review(state, quality=5)
    third = sm2_review(
        ReviewState(
            last_review=second.next_review,
            next_review=second.next_review,
            interval_days=second.interval_days,
            ease_factor=second.ease_factor,
            repetitions=second.repetitions,
        ),
        quality=5,
    )
    assert second.interval_days >= 6
    assert third.interval_days > second.interval_days


def test_fortran_bridge() -> None:
    left = [[1.0, 2.0], [3.0, 4.0]]
    right = [[5.0, 6.0], [7.0, 8.0]]
    result = multiply_matrices(left, right)
    assert result == [[19.0, 22.0], [43.0, 50.0]]


def test_dialectic_experiment_is_reproducible() -> None:
    first = run_dialectic_experiment(seeds=(7,), cohort_size=60)
    second = run_dialectic_experiment(seeds=(7,), cohort_size=60)
    assert first == second


def test_learning_path_payload_builder() -> None:
    payload = {
        "student_id": 1,
        "name": "Ada Student",
        "course_id": 1,
        "learning_style": "causal-visual",
        "concept_mastery": {
            "numeracy": 0.61,
            "fractions": 0.38,
            "equations": 0.49,
            "functions": 0.24,
            "systems": 0.29,
            "modeling": 0.15,
        },
        "recent_scores": [72, 84, 78],
        "target_concepts": ["modeling"],
    }
    response = build_learning_path_payload(payload)
    assert response["student_id"] == 1
    assert response["target_concepts"] == ["modeling"]
    assert response["ordered_steps"][0]["concept_id"] == "numeracy"
    assert response["ordered_steps"][0]["instrument_strength"] > 0.0


def test_learning_path_cli_contract() -> None:
    payload = {
        "student_id": 5,
        "name": "CLI Student",
        "course_id": 1,
        "concept_mastery": {
            "numeracy": 0.58,
            "fractions": 0.44,
            "equations": 0.34,
            "functions": 0.18,
            "systems": 0.22,
            "modeling": 0.1,
        },
        "recent_scores": [68, 70, 74],
        "target_concepts": ["modeling"],
    }
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src") + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "-m", "socrates_dialectic", "learning-path"],
        check=True,
        capture_output=True,
        cwd=root,
        env=env,
        input=json.dumps(payload),
        text=True,
    )
    response = json.loads(result.stdout)
    assert response["student_id"] == 5
    assert response["causal_gaps"]
    assert response["ordered_steps"][0]["causal_effect"] > 0.0
