"""Builds a fee-adjusted, normalised, and graded copy of a fund pool."""

import copy

from src.comparison.fees import apply_dmey_nihul
from src.comparison.grading import add_grade_and_sort
from src.comparison.normalization import normalize_data


def build_graded_pool(
    funds: list[dict],
    dmei_nihul: float,
    weight_1: int,
    weight_3: int,
    weight_5: int,
    weight_sharp: int,
) -> list[dict]:
    """Deep-copy a fund pool, apply fees, normalise, grade, and sort it.

    Args:
        funds: Source fund dicts (left unmodified).
        dmei_nihul: Annual management-fee percentage to deduct.
        weight_1: Weight for the 1-year cumulative return metric.
        weight_3: Weight for the 3-year average annual return metric.
        weight_5: Weight for the 5-year average annual return metric.
        weight_sharp: Weight for the Sharpe ratio metric.

    Returns:
        A new list of fund dicts, fee-adjusted, normalised, graded, and
        sorted from highest grade to lowest.
    """
    adjusted = apply_dmey_nihul(copy.deepcopy(funds), dmei_nihul)
    normalize_data(adjusted)
    return add_grade_and_sort(adjusted, weight_1, weight_3, weight_5, weight_sharp)
