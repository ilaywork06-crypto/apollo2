"""Adds normalized (0-100) variants of the fund metrics used by AmoScore."""

MIN_MAX_FIELDS = (
    "sharp_ribit_hasarot_sikun",
    "tsua_5",
    "tsua_3",
    "tsua_mitztaberet_letkufa",
)
LIQUIDITY_FIELD = "liquidity_index"


def has_metric(fund: dict, field: str) -> bool:
    """Return whether *fund* has real data for the metric *field*.

    The GemeNet parser reports a missing numeric field as ``0.0``, so a
    reported value of exactly zero means "no data" for returns and Sharpe.
    For a fee-adjusted return the reported (``<field>_gross``) value decides:
    a 0.25% return less a 0.25% fee is a real 0.0, not missing data. The
    liquidity index is ``None`` when unavailable, and zero is a real value.
    """
    if field == LIQUIDITY_FIELD:
        return fund.get(field) is not None
    reported = fund.get(f"{field}_gross", fund.get(field))
    return reported is not None and reported != 0.0


def normalize_data(funds_list: list[dict]) -> None:
    """Add normalised variants (0-100) of the AmoScore metrics.

    Returns and Sharpe are min-max normalised: for each field a new
    ``<field>_normalized`` key is added to every fund dict. Funds with a raw
    value of ``0.0`` receive a normalised score of ``0.0`` without affecting
    the normalisation range.

    The liquidity index is normalised by percentile rank instead (see
    :func:`normalize_liquidity`).

    Args:
        funds_list: List of fund dicts to enrich with normalised fields
            (modified in-place).
    """
    for field in MIN_MAX_FIELDS:
        values = [fund[field] for fund in funds_list if has_metric(fund, field)]
        if not values:
            for fund in funds_list:
                fund[field + "_normalized"] = 0.0
            continue
        min_value = min(values)
        max_value = max(values)
        for fund in funds_list:
            if has_metric(fund, field):
                fund[field + "_normalized"] = (
                    (fund[field] - min_value) / (max_value - min_value) * 100
                    if max_value > min_value
                    else 0.0
                )
            else:
                fund[field + "_normalized"] = 0.0
    normalize_liquidity(funds_list)


def normalize_liquidity(funds_list: list[dict]) -> None:
    """Add ``liquidity_index_normalized``: the fund's percentile rank (0-100) in the list.

    Funds are ranked by their distinct liquidity values: the highest net
    accumulation relative to assets gets ``100`` and the lowest (most
    negative — money leaving the fund) gets ``0``, with the values in between
    spaced evenly by rank. Funds that tie share a score, so a tie at either
    end still gets exactly ``100`` or ``0``. Funds without liquidity data get
    ``0.0`` and do not take part. With fewer than two distinct values there
    is nothing to rank, and every ranked fund gets the neutral ``50.0``.

    Args:
        funds_list: List of fund dicts to enrich (modified in-place).
    """
    for fund in funds_list:
        fund[LIQUIDITY_FIELD + "_normalized"] = 0.0
    distinct = sorted({f[LIQUIDITY_FIELD] for f in funds_list if has_metric(f, LIQUIDITY_FIELD)})
    last = len(distinct) - 1
    percentile = {value: i / last * 100 if last else 50.0 for i, value in enumerate(distinct)}
    for fund in funds_list:
        if has_metric(fund, LIQUIDITY_FIELD):
            fund[LIQUIDITY_FIELD + "_normalized"] = percentile[fund[LIQUIDITY_FIELD]]
