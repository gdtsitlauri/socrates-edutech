from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class ReviewState:
    last_review: date
    next_review: date
    interval_days: int
    ease_factor: float
    repetitions: int


def sm2_review(
    state: ReviewState,
    quality: int,
) -> ReviewState:
    """Advance spaced repetition state using the SM-2 algorithm."""

    quality = max(0, min(5, quality))
    ease_factor = max(
        1.3,
        state.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
    )

    if quality < 3:
        repetitions = 0
        interval_days = 1
    elif state.repetitions == 0:
        repetitions = 1
        interval_days = 1
    elif state.repetitions == 1:
        repetitions = 2
        interval_days = 6
    else:
        repetitions = state.repetitions + 1
        interval_days = max(1, round(state.interval_days * state.ease_factor))

    next_review = state.last_review + timedelta(days=interval_days)
    return ReviewState(
        last_review=state.last_review,
        next_review=next_review,
        interval_days=interval_days,
        ease_factor=round(ease_factor, 3),
        repetitions=repetitions,
    )
