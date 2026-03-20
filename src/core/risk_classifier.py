"""Module-level cache and helpers for classifying a kupa's equity-exposure risk level."""

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


def get_risk_level(kupa_id: int) -> str:
    """Return the risk-level label for a kupa based on its equity exposure.

    Risk bands:
    * ``"low"``    — equity exposure ≤ 24.9999 %
    * ``"medium"`` — equity exposure ≤ 74.9999 %
    * ``"high"``   — equity exposure > 74.9999 %
    * ``"invalid"`` — kupa ID not found in the risk map

    Args:
        kupa_id: Numeric identifier of the kupa to classify.

    Returns:
        One of ``"low"``, ``"medium"``, ``"high"``, or ``"invalid"``.
    """
    if kupa_id not in _risks:
        return "invalid"
    pct = _risks[kupa_id]
    if pct <= 24.9999:
        return "low"
    elif pct <= 74.9999:
        return "medium"
    else:
        return "high"
