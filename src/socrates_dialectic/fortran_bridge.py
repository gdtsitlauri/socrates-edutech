from __future__ import annotations

from typing import Sequence


def _reference_multiply(
    left: Sequence[Sequence[float]],
    right: Sequence[Sequence[float]],
) -> list[list[float]]:
    rows = len(left)
    cols = len(right[0])
    inner = len(right)
    return [
        [
            sum(left[row][index] * right[index][col] for index in range(inner))
            for col in range(cols)
        ]
        for row in range(rows)
    ]


def multiply_matrices(
    left: Sequence[Sequence[float]],
    right: Sequence[Sequence[float]],
) -> list[list[float]]:
    """Use the Fortran bridge when available and fall back otherwise."""

    try:
        import math_lib  # type: ignore

        api = getattr(math_lib, "math_lib", math_lib)
        product = api.matrix_multiply(left, right)  # pragma: no cover
        # f2py-backed calls can return NumPy arrays; normalize to the shared
        # list-of-lists contract used by tests and JSON-facing callers.
        return product.tolist() if hasattr(product, "tolist") else product
    except Exception:
        return _reference_multiply(left, right)
