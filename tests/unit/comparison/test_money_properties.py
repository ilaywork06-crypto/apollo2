"""Properties of the money figures: balance projections, upside from moving, portfolio score."""

import random

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.comparison.portfolio import HORIZONS, holding_upside, summarize_portfolio
from src.comparison.projections import calculate_potential_amount
from tests.conftest import make_fund
from tests.strategies import any_returns, balances, holding_results

_SUFFIX = {1: "", 3: "_3", 5: "_5"}


def _oracle_upside(holding, horizon, gross):
    """Independent restatement of the upside rule, for comparison."""
    client = holding["client"]
    suffix = _SUFFIX[horizon]

    def potential(option):
        if not option:
            return None
        source = option["gross"] if gross else option
        return source[f"potential_amount{suffix}"]

    candidates = [potential(holding["golden"])]
    if holding["alternatives"] and client["rank"] != 1:
        candidates.append(potential(holding["alternatives"][0]))
    candidates = [c for c in candidates if c is not None]
    return max([0.0] + [c - client["amount"] for c in candidates])


# ---------------------------------------------------------------------------
# Projections
# ---------------------------------------------------------------------------


class TestProjectionProperties:
    @given(balances, any_returns, any_returns, st.sampled_from([1, 3, 5]))
    def test_matches_the_compound_growth_formula(self, amount, current, better, years):
        result = calculate_potential_amount(
            amount, make_fund(tsua_5=current), make_fund(tsua_5=better), "tsua_5", years
        )
        expected = amount * (1 + better / 100) ** years / (1 + current / 100) ** years
        assert result == pytest.approx(expected, abs=0.006)

    @given(balances, any_returns, st.sampled_from([1, 3, 5]))
    def test_same_return_keeps_the_same_balance(self, amount, tsua, years):
        fund = make_fund(tsua_3=tsua)
        assert calculate_potential_amount(amount, fund, fund, "tsua_3", years) == pytest.approx(amount, abs=0.006)

    @given(balances, any_returns, any_returns, any_returns)
    def test_a_better_return_never_projects_less(self, amount, current, a, b):
        low, high = sorted((a, b))
        client = make_fund(tsua_1=current)
        assert calculate_potential_amount(amount, client, make_fund(tsua_1=low)) <= calculate_potential_amount(
            amount, client, make_fund(tsua_1=high)
        )

    @given(st.integers(1, 1_000_000), st.integers(2, 10), any_returns, any_returns)
    def test_projection_is_proportional_to_the_balance(self, amount, factor, current, better):
        client, option = make_fund(tsua_1=current), make_fund(tsua_1=better)
        single = calculate_potential_amount(amount, client, option)
        scaled = calculate_potential_amount(amount * factor, client, option)
        assert scaled == pytest.approx(single * factor, abs=0.01 * factor)

    def test_client_fund_that_lost_everything_keeps_the_balance(self):
        # A -100% return would divide by zero; the projection falls back to the balance
        wiped_out = make_fund(tsua_1=-100.0)
        assert calculate_potential_amount(1234.567, wiped_out, make_fund(tsua_1=10.0)) == 1234.57

    def test_defaults_to_one_year_of_the_one_year_return(self):
        client, option = make_fund(tsua_1=10.0, tsua_5=1.0), make_fund(tsua_1=21.0, tsua_5=99.0)
        assert calculate_potential_amount(110_000.0, client, option) == pytest.approx(121_000.0)


# ---------------------------------------------------------------------------
# Upside from moving
# ---------------------------------------------------------------------------


class TestUpsideProperties:
    # Every horizon and fee mode is checked on every example: sampling one per example
    # lets a bug in a single horizon slip through by chance.

    @given(holding_results())
    def test_matches_the_upside_rule(self, holding):
        for horizon in HORIZONS:
            for gross in (False, True):
                assert holding_upside(holding, horizon, gross) == pytest.approx(
                    round(_oracle_upside(holding, horizon, gross), 2)
                ), (horizon, gross)

    @given(holding_results())
    def test_never_negative(self, holding):
        assert all(holding_upside(holding, h, g) >= 0 for h in HORIZONS for g in (False, True))

    @given(holding_results())
    def test_no_fee_in_the_new_fund_never_gains_less(self, holding):
        for horizon in HORIZONS:
            assert holding_upside(holding, horizon, gross=True) >= holding_upside(holding, horizon, gross=False)

    def test_defaults_to_one_year_net_of_fees(self):
        option = {
            "grade": 90.0, "potential_amount": 104_000.0, "potential_amount_3": 130_000.0, "potential_amount_5": 150_000.0,
            "gross": {"potential_amount": 105_000.0, "potential_amount_3": 131_000.0, "potential_amount_5": 151_000.0},
        }
        holding = {"client": {"amount": 100_000.0, "grade": 50.0, "rank": 4}, "alternatives": [option], "golden": {}}
        assert holding_upside(holding) == 4_000.0

    def test_rounded_to_agorot(self):
        option = {"grade": 90.0, "potential_amount": 100_000.1234, "gross": {}}
        holding = {"client": {"amount": 100_000.0, "grade": 50.0, "rank": 4}, "alternatives": [option], "golden": {}}
        assert holding_upside(holding) == 0.12


# ---------------------------------------------------------------------------
# Portfolio summary
# ---------------------------------------------------------------------------


class TestPortfolioProperties:
    @given(st.lists(holding_results(), max_size=8))
    def test_weighted_score_lies_between_the_weakest_and_strongest_fund(self, holdings):
        summary = summarize_portfolio(holdings)
        grades = [h["client"]["grade"] for h in holdings if h["client"]["grade"] > 0]
        if not grades:
            assert summary["weighted_score"] is None
            return
        assert min(grades) - 0.05 <= summary["weighted_score"] <= max(grades) + 0.05

    @given(st.lists(holding_results(), max_size=8))
    def test_weighted_score_matches_the_money_weighted_mean(self, holdings):
        graded = [h for h in holdings if h["client"]["grade"] > 0]
        summary = summarize_portfolio(holdings)
        if graded:
            money = sum(h["client"]["amount"] for h in graded)
            expected = sum(h["client"]["grade"] * h["client"]["amount"] for h in graded) / money
            assert summary["weighted_score"] == round(expected, 1)

    @given(st.lists(holding_results(), max_size=8))
    def test_moving_to_the_best_alternative_never_lowers_the_score(self, holdings):
        summary = summarize_portfolio(holdings)
        if summary["weighted_score"] is not None:
            assert summary["potential_score"] >= summary["weighted_score"]

    @given(st.lists(holding_results(), max_size=8), st.randoms(use_true_random=False))
    def test_order_of_holdings_does_not_matter(self, holdings, rnd: random.Random):
        shuffled = holdings[:]
        rnd.shuffle(shuffled)
        first, second = summarize_portfolio(holdings), summarize_portfolio(shuffled)
        for key in ("weighted_score", "potential_score", "weighted_percentile", "coverage"):
            assert first[key] == pytest.approx(second[key], abs=0.1) if first[key] is not None else second[key] is None
        assert first["total_amount"] == pytest.approx(second["total_amount"])

    @given(st.lists(holding_results(), min_size=1, max_size=8))
    def test_upside_is_the_sum_over_holdings_for_every_horizon_and_mode(self, holdings):
        upside = summarize_portfolio(holdings)["upside"]
        for mode, gross in (("net", False), ("gross", True)):
            for horizon in HORIZONS:
                expected = sum(holding_upside(h, horizon, gross) for h in holdings)
                assert upside[mode][str(horizon)] == pytest.approx(expected, abs=0.01)

    @given(st.lists(holding_results(), max_size=8))
    def test_coverage_is_the_share_of_graded_money(self, holdings):
        summary = summarize_portfolio(holdings)
        total = sum(h["client"]["amount"] for h in holdings)
        graded = sum(h["client"]["amount"] for h in holdings if h["client"]["grade"] > 0)
        assert summary["coverage"] == (round(graded / total * 100, 1) if total else 0.0)
        assert summary["graded_amount"] == round(graded, 2)
        assert summary["holdings_count"] == len(holdings)


class TestPortfolioEdges:
    def _holding(self, amount, grade, percentile=50, alternatives=()):
        return {
            "client": {"amount": amount, "grade": grade, "rank": 5, "percentile": percentile},
            "alternatives": list(alternatives),
            "golden": {},
        }

    def test_scores_rounded_to_one_decimal(self):
        holdings = [self._holding(1.0, 10.0), self._holding(2.0, 20.0)]
        assert summarize_portfolio(holdings)["weighted_score"] == 16.7

    def test_a_fraction_of_a_point_still_counts_as_graded(self):
        summary = summarize_portfolio([self._holding(100.0, 0.5)])
        assert summary["weighted_score"] == 0.5
        assert summary["coverage"] == 100.0

    def test_no_alternatives_keeps_the_own_grade_as_potential(self):
        assert summarize_portfolio([self._holding(100.0, 0.5)])["potential_score"] == 0.5

    def test_worst_percentile_is_zero_not_missing(self):
        holdings = [self._holding(100.0, 40.0, percentile=0), self._holding(100.0, 60.0, percentile=0)]
        assert summarize_portfolio(holdings)["weighted_percentile"] == 0.0

    def test_small_graded_balance_still_scores(self):
        summary = summarize_portfolio([self._holding(0.5, 40.0)])
        assert (summary["weighted_score"], summary["coverage"]) == (40.0, 100.0)

    def test_upside_totals_are_rounded_to_agorot(self):
        def gaining(amount, potential):
            option = {"grade": 90.0, "potential_amount": potential, "potential_amount_3": None,
                      "potential_amount_5": None, "gross": {}}
            return {"client": {"amount": amount, "grade": 50.0, "rank": 5}, "alternatives": [option], "golden": {}}

        # 0.1 + 0.2 is 0.30000000000000004 in floating point
        upside = summarize_portfolio([gaining(100.0, 100.1), gaining(100.0, 100.2)])["upside"]["net"]["1"]
        assert upside == 0.3

    def test_empty_portfolio(self):
        summary = summarize_portfolio([])
        assert summary == {
            "total_amount": 0,
            "holdings_count": 0,
            "graded_amount": 0,
            "coverage": 0.0,
            "weighted_score": None,
            "potential_score": None,
            "weighted_percentile": None,
            "upside": {"net": {"1": 0, "3": 0, "5": 0}, "gross": {"1": 0, "3": 0, "5": 0}},
        }

    def test_amounts_rounded_to_agorot(self):
        summary = summarize_portfolio([self._holding(100.004, 50.0), self._holding(200.004, 0)])
        assert summary["total_amount"] == 300.01
        assert summary["graded_amount"] == 100.0
