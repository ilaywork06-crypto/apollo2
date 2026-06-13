"""Pure data-shaping helpers for building community profile and leaderboard payloads."""

import json
from datetime import date


def apply_percentages(funds: list[dict]) -> list[dict]:
    """Annotate each fund with its percentage share of the total amount.

    Args:
        funds: Fund dicts, each with an ``"amount"`` key.

    Returns:
        Copies of *funds* with a ``"pct_of_total"`` key added. If the total
        amount is zero, every fund is treated as a 0% share to avoid a
        division by zero.
    """
    total_amount = sum(f.get("amount", 0) for f in funds)
    if total_amount == 0:
        total_amount = 1
    return [
        {**f, "pct_of_total": round(f.get("amount", 0) / total_amount * 100, 1)}
        for f in funds
    ]


def weighted_tsua(funds_with_pct: list[dict]) -> float:
    """Compute the percentage-weighted average annual return (tsua)."""
    return sum(f["tsua_1"] * f["pct_of_total"] / 100 for f in funds_with_pct)


def weighted_score(funds_with_pct: list[dict]) -> float:
    """Compute the percentage-weighted average grade, ignoring non-positive grades."""
    return sum(
        f.get("grade", 0) * f["pct_of_total"] / 100
        for f in funds_with_pct
        if f.get("grade", 0) > 0
    )


def weighted_equity_exposure(funds_with_pct: list[dict]) -> float | None:
    """Compute the percentage-weighted average equity exposure.

    Returns:
        The weighted average, or ``None`` if no fund has equity-exposure
        data or the eligible funds carry zero total weight.
    """
    funds_with_exposure = [f for f in funds_with_pct if f.get("equity_exposure") is not None]
    if not funds_with_exposure:
        return None
    exposure_weight_total = sum(f["pct_of_total"] for f in funds_with_exposure)
    if exposure_weight_total <= 0:
        return None
    return (
        sum(f["equity_exposure"] * f["pct_of_total"] for f in funds_with_exposure)
        / exposure_weight_total
    )


def dominant_risk(funds_with_pct: list[dict]) -> str:
    """Return the risk level with the largest combined percentage share.

    Funds without a ``"risk_level"`` are treated as ``"high"``. If
    *funds_with_pct* is empty, returns ``"high"``.
    """
    risk_pct: dict[str, float] = {}
    for f in funds_with_pct:
        risk = f.get("risk_level", "high")
        risk_pct[risk] = risk_pct.get(risk, 0.0) + f["pct_of_total"]
    return max(risk_pct, key=risk_pct.get) if risk_pct else "high"


def to_funds_json(funds_with_pct: list[dict]) -> list[dict]:
    """Project each fund down to its public ``name``/``id``/``pct`` fields."""
    return [{"name": f["name"], "id": f["id"], "pct": f["pct_of_total"]} for f in funds_with_pct]


def today_str() -> str:
    """Return today's date formatted as ``DD/MM/YYYY``."""
    return date.today().strftime("%d/%m/%Y")


def build_profile_payload(
    fake_name: str,
    weighted_tsua_value: float,
    weighted_score_value: float,
    dominant_risk_value: str,
    weighted_equity_exposure_value: float | None,
    funds_json: list[dict],
    joined: str,
) -> dict:
    """Assemble the public profile dict returned from ``join_community``."""
    return {
        "fake_name": fake_name,
        "weighted_tsua": round(weighted_tsua_value, 2),
        "weighted_score": round(weighted_score_value, 2),
        "dominant_risk": dominant_risk_value,
        "weighted_equity_exposure": (
            round(weighted_equity_exposure_value, 1)
            if weighted_equity_exposure_value is not None
            else None
        ),
        "funds": funds_json,
        "joined": joined,
    }


def shorten_join_date(joined_full: str) -> str:
    """Convert a ``DD/MM/YYYY`` date string to ``MM/YYYY``.

    Returns *joined_full* unchanged if it doesn't have exactly three
    ``/``-separated parts.
    """
    try:
        parts = joined_full.split("/")
        return f"{parts[1]}/{parts[2]}" if len(parts) == 3 else joined_full
    except Exception:
        return joined_full


def _funds_from_row(raw_funds) -> list[dict]:
    if isinstance(raw_funds, str):
        return json.loads(raw_funds)
    return raw_funds or []


def to_leaderboard_row(row) -> dict:
    """Shape a raw ``profiles`` row into a leaderboard entry."""
    funds = _funds_from_row(row["funds"])
    return {
        "fake_name": row["fake_name"],
        "weighted_tsua": row["weighted_tsua"],
        "weighted_score": row["weighted_score"],
        "dominant_risk": row["dominant_risk"],
        "weighted_equity_exposure": row["weighted_equity_exposure"],
        "num_funds": len(funds),
        "joined": shorten_join_date(row["joined"] or ""),
    }


def to_profile_dict(row) -> dict:
    """Shape a raw ``profiles`` row into a full profile dict."""
    return {
        "fake_name": row["fake_name"],
        "weighted_tsua": row["weighted_tsua"],
        "weighted_score": row["weighted_score"],
        "dominant_risk": row["dominant_risk"],
        "weighted_equity_exposure": row["weighted_equity_exposure"],
        "joined": row["joined"],
        "funds": _funds_from_row(row["funds"]),
    }
