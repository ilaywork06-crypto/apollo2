"""Summarises a client's whole portfolio from its per-holding comparison results."""

HORIZONS = (1, 3, 5)
_SUFFIX = {1: "", 3: "_3", 5: "_5"}


def _option_potential(option: dict | None, horizon: int, gross: bool) -> float | None:
    if not option:
        return None
    source = option.get("gross", {}) if gross else option
    return source.get(f"potential_amount{_SUFFIX[horizon]}")


def holding_upside(holding: dict, horizon: int = 1, gross: bool = False) -> float:
    """Return the NIS a holding would have gained by moving to its best option.

    Mirrors the results page: the top same-risk alternative counts only when
    the client's fund isn't already ranked first, and the golden (higher-risk)
    option counts whenever it was offered. Options without comparable data for
    the horizon are ignored.

    Args:
        holding: One per-holding result with ``client``, ``alternatives`` and
            ``golden`` keys, as produced by the comparison service.
        horizon: Look-back in years — ``1``, ``3`` or ``5``.
        gross: Use the alternatives' gross (pre-fee) projections instead of the
            ones net of the client's management fee.

    Returns:
        The gain in NIS, or ``0.0`` when staying put is at least as good.
    """
    client = holding["client"]
    amount = client["amount"]
    candidates = [_option_potential(holding.get("golden"), horizon, gross)]
    alternatives = holding.get("alternatives") or []
    if alternatives and client.get("rank") != 1:
        candidates.append(_option_potential(alternatives[0], horizon, gross))
    best = max((c for c in candidates if c is not None), default=amount)
    return round(max(0.0, best - amount), 2)


def _is_graded(client: dict) -> bool:
    """Whether the holding's fund could be scored (``grade`` 0 alone is ambiguous)."""
    return client.get("has_grade", (client.get("grade") or 0) > 0)


def _upside_by_horizon(holdings: list[dict], gross: bool) -> dict[str, float]:
    return {
        str(horizon): round(sum(holding_upside(h, horizon, gross) for h in holdings), 2)
        for horizon in HORIZONS
    }


def summarize_portfolio(holdings: list[dict]) -> dict:
    """Weight each holding's AmoScore by the share of the client's money in it.

    Holdings whose fund could not be scored (not enough data, e.g. a
    brand-new fund — ``has_grade`` false) are left out of the weighting instead
    of dragging the score down, and the share of money that *was* scored is
    reported as ``coverage``. A fund that is scored and simply weakest on every
    metric counts with its grade of ``0``.
    ``potential_score`` is the same weighted score if every holding moved to
    its best same-risk alternative (or stayed, when it is already the best).

    Args:
        holdings: Per-holding results with ``client``, ``alternatives`` and
            ``golden`` keys.

    Returns:
        A dict with ``total_amount``, ``holdings_count``, ``graded_amount``,
        ``coverage`` (percent), ``weighted_score``, ``potential_score`` and
        ``weighted_percentile`` (``None`` when no holding could be scored),
        plus ``upside`` — the NIS gain from moving, as
        ``{"net"|"gross": {"1"|"3"|"5": amount}}``.
    """
    total_amount = sum(h["client"]["amount"] for h in holdings)
    graded = [h for h in holdings if _is_graded(h["client"])]
    graded_amount = sum(h["client"]["amount"] for h in graded)

    def weighted(value_of) -> float | None:
        if graded_amount <= 0:
            return None
        return round(sum(value_of(h) * h["client"]["amount"] for h in graded) / graded_amount, 1)

    def best_grade(h: dict) -> float:
        alternatives = h.get("alternatives") or []
        top = alternatives[0]["grade"] if alternatives else 0
        return max(h["client"]["grade"], top)

    return {
        "total_amount": round(total_amount, 2),
        "holdings_count": len(holdings),
        "graded_amount": round(graded_amount, 2),
        "coverage": round(graded_amount / total_amount * 100, 1) if total_amount > 0 else 0.0,
        "weighted_score": weighted(lambda h: h["client"]["grade"]),
        "potential_score": weighted(best_grade),
        "weighted_percentile": weighted(lambda h: h["client"].get("percentile") or 0),
        "upside": {
            "net": _upside_by_horizon(holdings, gross=False),
            "gross": _upside_by_horizon(holdings, gross=True),
        },
    }
