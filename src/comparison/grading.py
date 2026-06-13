"""Computes weighted composite grades and ranks funds by grade."""


def calculate_grade(
    fund: dict,
    weight_1: int,
    weight_3: int,
    weight_5: int,
    weight_sharp: int,
) -> float:
    """Compute a weighted composite score for a single fund.

    All four normalised metrics must be non-zero for a grade to be calculated;
    otherwise ``0`` is returned to indicate insufficient data.

    Args:
        fund: Fund dict that already contains normalised performance fields.
        weight_1: Weight for the 1-year cumulative return (normalised).
        weight_3: Weight for the 3-year average annual return (normalised).
        weight_5: Weight for the 5-year average annual return (normalised).
        weight_sharp: Weight for the Sharpe ratio (normalised).

    Returns:
        A weighted composite score rounded to two decimal places, or ``0`` if
        any of the required normalised fields are zero.
    """
    weights = {}

    if fund.get("tsua_mitztaberet_letkufa_normalized") != 0.0:
        weights["tsua_mitztaberet_letkufa_normalized"] = weight_1
    if fund.get("tsua_3_normalized") != 0.0:
        weights["tsua_3_normalized"] = weight_3
    if fund.get("tsua_5_normalized") != 0.0:
        weights["tsua_5_normalized"] = weight_5
    if fund.get("sharp_ribit_hasarot_sikun_normalized") != 0.0:
        weights["sharp_ribit_hasarot_sikun_normalized"] = weight_sharp

    if not weights:
        return 0
    total_weight = sum(weights.values())
    if total_weight != 100:
        return 0
    grade = 0
    for field, weight in weights.items():
        grade += fund[field] * (weight / total_weight)
    return round(grade, 2)


def add_grade_and_sort(
    funds_list: list[dict],
    weight_1: int,
    weight_3: int,
    weight_5: int,
    weight_sharp: int,
) -> list[dict]:
    """Assign a composite grade to each fund and return them sorted descending.

    Args:
        funds_list: List of fund dicts with normalised performance fields.
        weight_1: Weight for the 1-year cumulative return metric.
        weight_3: Weight for the 3-year average annual return metric.
        weight_5: Weight for the 5-year average annual return metric.
        weight_sharp: Weight for the Sharpe ratio metric.

    Returns:
        The same list sorted from highest grade to lowest, with a ``grade``
        key added to every fund dict.
    """
    for fund in funds_list:
        fund["grade"] = calculate_grade(fund, weight_1, weight_3, weight_5, weight_sharp)

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
