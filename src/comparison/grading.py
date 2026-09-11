"""Computes weighted composite grades and ranks funds by grade."""

from src.comparison.normalization import LIQUIDITY_FIELD, has_metric


def _weighted_fields(weight_1, weight_3, weight_5, weight_sharp, weight_liquidity) -> dict[str, int]:
    return {
        "tsua_mitztaberet_letkufa": weight_1,
        "tsua_3": weight_3,
        "tsua_5": weight_5,
        "sharp_ribit_hasarot_sikun": weight_sharp,
        LIQUIDITY_FIELD: weight_liquidity,
    }


def has_grade(
    fund: dict,
    weight_1: int,
    weight_3: int,
    weight_5: int,
    weight_sharp: int,
    weight_liquidity: int = 0,
) -> bool:
    """Return whether :func:`calculate_grade` can score *fund* with these weights.

    A grade of ``0`` is ambiguous: it is both the score of a fund that is the
    weakest on every weighted metric and the marker for "not enough data".
    This tells the two apart.
    """
    weights = _weighted_fields(weight_1, weight_3, weight_5, weight_sharp, weight_liquidity)
    if sum(weights.values()) != 100:
        return False
    return all(has_metric(fund, field) for field, weight in weights.items() if weight != 0)


def calculate_grade(
    fund: dict,
    weight_1: int,
    weight_3: int,
    weight_5: int,
    weight_sharp: int,
    weight_liquidity: int = 0,
) -> float:
    """Compute a weighted composite score for a single fund.

    Every metric with a non-zero weight must have data for a grade to be
    calculated; otherwise ``0`` is returned to indicate insufficient data.
    Whether a metric has data is judged from its raw value (see
    :func:`src.comparison.normalization.has_metric`), so a fund that merely
    scores the minimum (``0``) on a metric still gets a real grade.

    Args:
        fund: Fund dict that already contains normalised performance fields.
        weight_1: Weight for the 1-year cumulative return (normalised).
        weight_3: Weight for the 3-year average annual return (normalised).
        weight_5: Weight for the 5-year average annual return (normalised).
        weight_sharp: Weight for the Sharpe ratio (normalised).
        weight_liquidity: Weight for the liquidity index (percentile rank).

    Returns:
        A weighted composite score rounded to two decimal places, or ``0`` if
        the weights don't sum to 100 or a weighted metric has no data.
    """
    if not has_grade(fund, weight_1, weight_3, weight_5, weight_sharp, weight_liquidity):
        return 0
    weights = _weighted_fields(weight_1, weight_3, weight_5, weight_sharp, weight_liquidity)
    grade = sum(fund[field + "_normalized"] * (weight / 100) for field, weight in weights.items() if weight)
    return round(grade, 2)


def add_grade_and_sort(
    funds_list: list[dict],
    weight_1: int,
    weight_3: int,
    weight_5: int,
    weight_sharp: int,
    weight_liquidity: int = 0,
) -> list[dict]:
    """Assign a composite grade to each fund and return them sorted descending.

    Args:
        funds_list: List of fund dicts with normalised performance fields.
        weight_1: Weight for the 1-year cumulative return metric.
        weight_3: Weight for the 3-year average annual return metric.
        weight_5: Weight for the 5-year average annual return metric.
        weight_sharp: Weight for the Sharpe ratio metric.
        weight_liquidity: Weight for the liquidity index metric.

    Returns:
        The same list sorted from highest grade to lowest, with ``grade`` and
        ``has_grade`` (see :func:`has_grade`) keys added to every fund dict.
    """
    weights = (weight_1, weight_3, weight_5, weight_sharp, weight_liquidity)
    for fund in funds_list:
        fund["has_grade"] = has_grade(fund, *weights)
        fund["grade"] = calculate_grade(fund, *weights)

    return sorted(funds_list, key=lambda x: x["grade"], reverse=True)


def get_top_3(sorted_funds: list[dict]) -> list[dict]:
    """Return the top three funds from an already-sorted list.

    Args:
        sorted_funds: Funds list sorted from best to worst grade.

    Returns:
        The first three elements of *sorted_funds* (fewer if the list is
        shorter than three).
    """
    return sorted_funds[:3]
