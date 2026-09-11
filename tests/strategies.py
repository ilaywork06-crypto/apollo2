"""Hypothesis strategies shared by the property-based tests.

Numbers are drawn on coarse binary grids (multiples of 0.25, integers) so that
fee subtraction and min-max normalisation are exact in floating point. That
lets metamorphic properties ("the same pool with a different fee grades the
same") be asserted with ``==`` instead of fuzzy tolerances.

Each fund is drawn as one tuple of plain integers — several times faster to
generate than drawing every field separately.
"""

from hypothesis import strategies as st

from tests.conftest import make_fund, make_mislaka

SUGS = ("תגמולים ואישית לפיצויים", "קרנות השתלמות")
RISK_LEVELS = ("low", "medium", "high")
HEVROT = ("A", "B", "C")


def quarters(min_value: float, max_value: float, nonzero: bool = True):
    """Multiples of 0.25 in [min_value, max_value] (0.0 is the parser's 'missing' marker)."""
    values = st.integers(int(min_value * 4), int(max_value * 4)).map(lambda n: n / 4)
    return values.filter(lambda v: v != 0.0) if nonzero else values


any_returns = quarters(-15.0, 40.0)
fees = st.integers(0, 4).map(lambda n: n / 4)  # 0, 0.25 … 1.0
balances = st.integers(1, 2_000_000).map(float)


def _fund_rows(returns):
    return st.tuples(
        st.integers(0, len(HEVROT) - 1),
        st.integers(0, len(SUGS) - 1),
        st.integers(0, len(RISK_LEVELS) - 1),
        returns, returns, returns,
        st.integers(1, 60),     # Sharpe × 20
        st.integers(0, 120),    # equity exposure
        st.integers(-1, 120),   # foreign exposure (-1 = unknown)
        st.integers(-300, 300), # liquidity index
    )


def _build_fund(index: int, row: tuple, **fixed) -> dict:
    hevra, sug, risk, tsua_1, tsua_3, tsua_5, sharpe, equity, foreign, liquidity = row
    params = dict(
        fund_id=str(index + 1),
        hevra=HEVROT[hevra],
        sug=SUGS[sug],
        risk_level=RISK_LEVELS[risk],
        tsua_1=tsua_1, tsua_3=tsua_3, tsua_5=tsua_5,
        sharpe=sharpe / 20,
        equity_exposure=float(equity),
        foreign_exposure=None if foreign < 0 else float(foreign),
        liquidity_index=float(liquidity),
    )
    params.update(fixed)
    return make_fund(**params)


def fund_lists(min_size: int = 1, max_size: int = 12, returns=any_returns, **fixed):
    """Funds with complete data and distinct IDs ("1", "2", …); *fixed* overrides fields."""
    return st.lists(_fund_rows(returns), min_size=min_size, max_size=max_size).map(
        lambda rows: [_build_fund(i, row, **fixed) for i, row in enumerate(rows)]
    )


@st.composite
def comparison_cases(draw, returns=any_returns):
    """A fund universe plus one client holding in one of its funds.

    Returns ``(all_funds, suggestable, client_fund, mislaka)``. Some funds are
    left out of the recommendable subset to model special-population funds
    and excluded companies.
    """
    all_funds = draw(fund_lists(min_size=2, max_size=12, returns=returns))
    hidden = draw(st.sets(st.sampled_from([f["ID"] for f in all_funds]), max_size=len(all_funds) // 2))
    suggestable = [f for f in all_funds if f["ID"] not in hidden]
    client_fund = draw(st.sampled_from(all_funds))
    mislaka = make_mislaka(client_fund["ID"], balance=draw(balances), dmei_nihul_tzvira=draw(fees))
    return all_funds, suggestable, client_fund, mislaka


@st.composite
def options(draw):
    """A recommended fund's grade and projections; gross is never below net (the fee is >= 0)."""
    horizons = ("", "_3", "_5")
    net = {h: draw(st.none() | st.integers(0, 3_000_000).map(float)) for h in horizons}
    gross = {h: None if net[h] is None else net[h] + draw(st.integers(0, 50_000)) for h in horizons}
    return {
        "grade": draw(st.integers(1, 100).map(float)),
        **{f"potential_amount{h}": net[h] for h in horizons},
        "gross": {f"potential_amount{h}": gross[h] for h in horizons},
    }


@st.composite
def holding_results(draw):
    """A per-holding result as produced by the comparison service (money fields only)."""
    alternatives = sorted(draw(st.lists(options(), max_size=3)), key=lambda a: a["grade"], reverse=True)
    return {
        "client": {
            "amount": draw(balances),
            "grade": draw(st.just(0.0) | st.integers(1, 100).map(float)),
            "rank": draw(st.integers(1, 20)),
            "percentile": draw(st.integers(0, 100)),
        },
        "alternatives": alternatives,
        "golden": draw(st.just({}) | options()),
    }
