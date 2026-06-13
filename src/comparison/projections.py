"""Projects a client's future balance under an alternative fund's historical returns."""


def calculate_potential_amount(
    current_amount: float, current_fund: dict, better_fund: dict,
    field: str = "tsua_mitztaberet_letkufa",
    years: int = 1,
) -> float:
    """Answer: "If I had migrated to the better fund N years ago, how much would I have today?"

    Back-calculates the client's starting balance N years ago (by reversing the
    current fund's return), then grows that same starting balance at the better
    fund's historical rate for N years to produce a "today" value.

    Equivalent formula:  current_amount x (1 + better_return%)^N
                                         ------------------------
                                          (1 + current_return%)^N

    Args:
        current_amount: The client's current accumulated savings balance.
        current_fund: Dict for the client's current fund.
        better_fund: Dict for the comparison fund.
        field: Return field to use (default: 1-year cumulative return).
        years: How many years back to project (1 -> 1-year return, 3 -> 3-year, 5 -> 5-year).

    Returns:
        What the balance would be today had the client been in the better fund
        for the past *years* years, rounded to two decimal places.
    """
    current_return = current_fund[field]
    better_return = better_fund[field]
    denominator = (1 + current_return / 100) ** years
    if denominator == 0:
        return round(current_amount, 2)
    potential = current_amount * (1 + better_return / 100) ** years / denominator
    return round(potential, 2)
