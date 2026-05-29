"""Module-level cache and helpers for classifying a fund's equity-exposure risk level."""

from pathlib import Path

_risks: dict[int, float] = {}


def load(path: Path) -> None:
    """Populate the risk map from an XML file. Safe to call multiple times.

    Subsequent calls are no-ops once the internal cache has been populated.

    Args:
        path: Filesystem path to the risks-map XML file.
    """
    if _risks:
        return
    from src.parsers.risk_map_parser import parse_risk_map
    _risks.update(parse_risk_map(path))


def get_equity_exposure(fund_id: int) -> float | None:
    """Return the raw equity-exposure percentage for a fund, or None if unknown."""
    return _risks.get(fund_id)


def get_risk_level(fund_id: int, low_exposure_threshold: int, medium_exposure_threshold: int) -> str:
    """Return the risk-level label for a fund based on its equity exposure.

    Risk bands:
    * ``"low"``    — equity exposure ≤ 25 %
    * ``"medium"`` — equity exposure ≤ 75 %
    * ``"high"``   — equity exposure > 75 %
    * ``"invalid"`` — fund ID not found in the risk map

    Args:
        fund_id: Numeric identifier of the fund to classify.

    Returns:
        One of ``"low"``, ``"medium"``, ``"high"``, or ``"invalid"``.
    """
    if fund_id not in _risks:
        return "invalid"
    pct = _risks[fund_id]
    if pct <= low_exposure_threshold:
        return "low"
    elif pct <= medium_exposure_threshold:
        return "medium"
    else:
        return "high"
