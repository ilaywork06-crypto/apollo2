"""Applies management fees to fund performance fields."""

RETURN_FIELDS = ("tsua_mitztaberet_letkufa", "tsua_3", "tsua_5")


def apply_dmey_nihul(funds_list: list[dict], dmey_nihul: float) -> list[dict]:
    """Subtract management fees from the return fields of each fund in-place.

    The fee comes off every reported return, gains and losses alike — a fund
    that lost 2% cost its members 2% plus the fee. A return of exactly ``0.0``
    is the parser's "no data" marker and is left alone. The pre-fee value of
    every return field is kept under ``<field>_gross`` so callers can still
    show gross returns.

    Args:
        funds_list: List of fund dicts to adjust (modified in-place).
        dmey_nihul: Annual management-fee percentage to deduct.

    Returns:
        The same list with adjusted return values.
    """
    for fund in funds_list:
        for field in RETURN_FIELDS:
            fund[f"{field}_gross"] = fund[field]
            if fund[field] != 0.0:
                fund[field] -= dmey_nihul
    return funds_list
