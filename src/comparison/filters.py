"""Filters fund lists by management-company blacklist."""


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
