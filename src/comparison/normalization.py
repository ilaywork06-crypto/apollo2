"""Adds min-max normalized variants of fund performance fields."""


def normalize_data(funds_list: list[dict]) -> None:
    """Add min-max normalised variants (0-100) of the key performance fields.

    For each of the four performance fields, a new ``<field>_normalized`` key
    is added to every fund dict.  Funds with a raw value of ``0.0`` receive a
    normalised score of ``0.0`` without affecting the normalisation range.

    Args:
        funds_list: List of fund dicts to enrich with normalised fields
            (modified in-place).
    """
    fields = [
        "sharp_ribit_hasarot_sikun",
        "tsua_5",
        "tsua_3",
        "tsua_mitztaberet_letkufa",
    ]
    for field in fields:
        values = [fund[field] for fund in funds_list if fund[field] != 0.0]
        if not values:
            for fund in funds_list:
                fund[field + "_normalized"] = 0.0
            continue
        min_value = min(values)
        max_value = max(values)
        for fund in funds_list:
            if fund[field] != 0.0:
                fund[field + "_normalized"] = (
                    (fund[field] - min_value) / (max_value - min_value) * 100
                    if max_value > min_value
                    else 0.0
                )
            else:
                fund[field + "_normalized"] = 0.0
