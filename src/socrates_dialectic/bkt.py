from __future__ import annotations


def _clamp(value: float, minimum: float = 1e-6, maximum: float = 1 - 1e-6) -> float:
    return max(minimum, min(maximum, value))


def bkt_update(
    prior: float,
    correct: bool,
    p_learn: float = 0.15,
    p_slip: float = 0.1,
    p_guess: float = 0.2,
) -> float:
    """Update the mastery estimate for a single observation.

    The posterior is updated with Bayes' rule and then advanced by the
    probability of learning during the step.
    """

    prior = _clamp(prior)
    p_learn = _clamp(p_learn, 0.0, 1.0)
    p_slip = _clamp(p_slip, 0.0, 1.0)
    p_guess = _clamp(p_guess, 0.0, 1.0)

    if correct:
        evidence = prior * (1 - p_slip)
        alternative = (1 - prior) * p_guess
    else:
        evidence = prior * p_slip
        alternative = (1 - prior) * (1 - p_guess)

    posterior = evidence / (evidence + alternative)
    posterior = posterior + (1 - posterior) * p_learn
    return _clamp(posterior)
