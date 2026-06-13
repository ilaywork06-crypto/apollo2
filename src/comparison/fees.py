"""Applies management fees to fund performance fields."""


def apply_dmey_nihul(funds_list: list[dict], dmey_nihul: float) -> list[dict]:
    """Subtract management fees from the return fields of each fund in-place.

    Only subtracts when the return value is positive, to avoid distorting funds
    with missing or zero data.

    Args:
        funds_list: List of fund dicts to adjust (modified in-place).
        dmey_nihul: Annual management-fee percentage to deduct.

    Returns:
        The same list with adjusted return values.
    """
    for fund in funds_list:
        if fund["tsua_5"] > 0.0:
            fund["tsua_5"] -= dmey_nihul
        if fund["tsua_3"] > 0.0:
            fund["tsua_3"] -= dmey_nihul
        if fund["tsua_mitztaberet_letkufa"] > 0.0:
            fund["tsua_mitztaberet_letkufa"] -= dmey_nihul
    return funds_list
