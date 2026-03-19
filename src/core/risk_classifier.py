_risks: dict = {}


def load(path) -> None:
    """Populate the risk map from an XML file. Safe to call multiple times."""
    if _risks:
        return
    from src.parsers.risk_map_parser import parse_risk_map
    _risks.update(parse_risk_map(path))


def get_risk_level(kupa_id: int) -> str:
    if kupa_id not in _risks:
        return "invalid"
    pct = _risks[kupa_id]
    if pct <= 24.9999:
        return "low"
    elif pct <= 74.9999:
        return "medium"
    else:
        return "high"
