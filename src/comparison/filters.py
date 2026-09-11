"""Filters fund lists by management-company blacklist and equity geography."""


def remove_bad_hevrot(list_of_funds: list[dict], bad_hevrot: list[str]) -> list[dict]:
    """Remove records with invalid or excluded company names.

    Args:
        list_of_funds: A list of fund dicts, each containing a ``hevra`` key.
        bad_hevrot: A set of company names to exclude.

    Returns:
        A filtered list of fund dicts, excluding those whose ``hevra`` value
        is in the predefined set of bad company names.
    """
    return [fund for fund in list_of_funds if fund["hevra"] not in bad_hevrot]


def filter_by_israel_equity_share(
    list_of_funds: list[dict], min_share: float = 0.0, max_share: float = 100.0
) -> list[dict]:
    """Keep funds whose equity component is invested in Israel within a range.

    The Israeli share is the ``israel_equity_share`` field — the Israeli
    percentage of the fund's equity (the rest is abroad). The full range
    ``0–100`` means "no preference" and returns the list unchanged. When a
    narrower range is set, funds whose share is unknown (no equity, or missing
    exposure data) are excluded, since they cannot be shown to match.

    Args:
        list_of_funds: Fund dicts, each with an ``israel_equity_share`` key.
        min_share: Lowest acceptable Israeli share of the equity, in percent.
        max_share: Highest acceptable Israeli share of the equity, in percent.

    Returns:
        The funds whose Israeli equity share lies within
        ``[min_share, max_share]``.
    """
    if min_share <= 0 and max_share >= 100:
        return list_of_funds
    return [
        fund
        for fund in list_of_funds
        if fund.get("israel_equity_share") is not None
        and min_share <= fund["israel_equity_share"] <= max_share
    ]
