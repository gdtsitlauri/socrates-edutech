from __future__ import annotations

import math
from collections.abc import Iterable


def irt_probability(theta: float, difficulty: float, discrimination: float = 1.0) -> float:
    exponent = -discrimination * (theta - difficulty)
    return 1.0 / (1.0 + math.exp(exponent))


def estimate_theta_binary(
    responses: Iterable[int],
    difficulties: Iterable[float],
    discrimination: float = 1.0,
    learning_rate: float = 0.05,
    steps: int = 400,
) -> float:
    """Estimate ability with simple gradient ascent on a 2PL log-likelihood."""

    response_list = list(responses)
    difficulty_list = list(difficulties)
    if len(response_list) != len(difficulty_list):
        raise ValueError("responses and difficulties must have the same length")

    theta = 0.0
    for _ in range(steps):
        gradient = 0.0
        for response, difficulty in zip(response_list, difficulty_list, strict=True):
            probability = irt_probability(theta, difficulty, discrimination)
            gradient += discrimination * (response - probability)
        theta += learning_rate * gradient / max(1, len(response_list))
        theta = max(-3.0, min(3.0, theta))
    return theta


def select_next_difficulty(theta: float) -> str:
    if theta < -0.5:
        return "foundational"
    if theta > 0.75:
        return "stretch"
    return "core"
