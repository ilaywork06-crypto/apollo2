"""Matches Mislaka holdings to GemeNet fund records and filters by risk level."""


def find_matching_funds(
    mislaka_list: list[dict], funds_list: list[dict]
) -> list[tuple[dict, dict]]:
    """Match each Mislaka entry to its corresponding fund in the GemeNet list.

    Args:
        mislaka_list: Parsed records from one or more Mislaka XML files.
        funds_list: Full list of fund records from the GemeNet XML file.

    Returns:
        A list of ``(mislaka_record, fund_record)`` pairs where the GemeNet ID
        found in the Mislaka record exists in the fund lookup table.
    """
    funds_by_id = {fund["ID"]: fund for fund in funds_list}
    return [
        (mislaka, funds_by_id[mislaka["GEMELNET_ID"]])
        for mislaka in mislaka_list
        if mislaka["GEMELNET_ID"] in funds_by_id
    ]


def get_funds_by_risk_level(funds_list: list[dict], risk_level: str) -> list[dict]:
    """Filter a list of funds to only those matching the given risk level.

    Args:
        funds_list: List of fund dicts, each containing a ``risk_level`` key.
        risk_level: The target risk level string (e.g. ``"low"``, ``"medium"``,
            ``"high"``).

    Returns:
        A filtered list of fund dicts whose ``risk_level`` equals *risk_level*.
    """
    return [fund for fund in funds_list if fund["risk_level"] == risk_level]
