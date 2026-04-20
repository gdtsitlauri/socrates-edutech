from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from .models import LearningPathResult, StudentProfile
from .optimizer import optimize_learning_path
from .simulation import build_demo_graph


def _estimate_ability(recent_scores: list[float]) -> float:
    if not recent_scores:
        return 0.0
    average_score = sum(recent_scores) / len(recent_scores)
    normalized = (average_score - 70.0) / 15.0
    return round(max(-3.0, min(3.0, normalized)), 4)


def _student_from_payload(payload: dict[str, Any]) -> tuple[StudentProfile, list[str] | None]:
    recent_scores = [float(score) for score in payload.get("recent_scores", [])]
    concept_mastery = {
        str(concept_id): float(mastery)
        for concept_id, mastery in payload.get("concept_mastery", {}).items()
    }
    student = StudentProfile(
        student_id=int(payload["student_id"]),
        name=str(payload.get("name", "Student")),
        course_id=int(payload["course_id"]),
        learning_style=str(payload.get("learning_style", "adaptive")),
        concept_mastery=concept_mastery,
        recent_scores=recent_scores,
        ability=float(payload.get("ability", _estimate_ability(recent_scores))),
    )

    raw_targets = payload.get("target_concepts")
    target_concepts = [str(item) for item in raw_targets] if raw_targets else None
    return student, target_concepts


def build_learning_path_payload(payload: dict[str, Any]) -> dict[str, Any]:
    graph = build_demo_graph()
    student, target_concepts = _student_from_payload(payload)
    result = optimize_learning_path(graph, student, target_concepts=target_concepts)
    return _serialize_learning_path(student.student_id, result)


def _serialize_learning_path(student_id: int, result: LearningPathResult) -> dict[str, Any]:
    return {
        "student_id": student_id,
        "target_concepts": list(result.target_concepts),
        "causal_gaps": [asdict(item) for item in result.causal_gaps],
        "ordered_steps": [asdict(item) for item in result.ordered_steps],
        "estimated_gain_per_hour": result.estimated_gain_per_hour,
        "generated_at": datetime.now(UTC).isoformat(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="socrates-dialectic")
    subparsers = parser.add_subparsers(dest="command", required=True)

    learning_path_parser = subparsers.add_parser("learning-path", help="Generate a DIALECTIC learning path from stdin JSON")
    learning_path_parser.add_argument("--pretty", action="store_true", help="Pretty-print the JSON response")

    args = parser.parse_args(argv)
    if args.command == "learning-path":
        payload = json.load(sys.stdin)
        response = build_learning_path_payload(payload)
        dump_kwargs = {"indent": 2, "sort_keys": True} if args.pretty else {"sort_keys": True}
        print(json.dumps(response, **dump_kwargs))
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
