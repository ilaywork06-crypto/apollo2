"""Finds a client's fund's rank within a sorted peer list."""

from typing import Optional


def get_client_ranking(
    sorted_funds: list[dict], client_fund_id: str
) -> tuple[Optional[int], int]:
    """Find the 1-based rank of the client's fund within a sorted list.

    Args:
        sorted_funds: Funds list sorted from best to worst grade.
        client_fund_id: The ``ID`` string of the client's current fund.

    Returns:
        A tuple of ``(rank, total)`` where *rank* is the 1-based position of
        the client's fund (or ``None`` if not found) and *total* is the length
        of *sorted_funds*.
    """
    for i, fund in enumerate(sorted_funds):
        if fund["ID"] == client_fund_id:
            return i + 1, len(sorted_funds)
    return None, len(sorted_funds)
