"""Unit tests for src/comparison/portfolio.py"""

import pytest

from src.comparison.portfolio import holding_upside, summarize_portfolio


def _option(grade, potential, gross_potential=None, potential_3=None):
    return {
        "grade": grade,
        "potential_amount": potential,
        "potential_amount_3": potential_3,
        "potential_amount_5": None,
        "gross": {
            "potential_amount": gross_potential if gross_potential is not None else potential,
            "potential_amount_3": potential_3,
            "potential_amount_5": None,
        },
    }


def _holding(amount, grade, rank=3, alternatives=None, golden=None, percentile=50):
    return {
        "client": {"amount": amount, "grade": grade, "rank": rank, "percentile": percentile},
        "alternatives": alternatives or [],
        "golden": golden or {},
    }


class TestHoldingUpside:
    def test_gain_from_best_alternative(self):
        h = _holding(100_000, 50, alternatives=[_option(90, 104_000)])
        assert holding_upside(h) == 4_000

    def test_golden_beats_alternative(self):
        h = _holding(100_000, 50, alternatives=[_option(90, 104_000)], golden=_option(95, 109_000))
        assert holding_upside(h) == 9_000

    def test_alternative_ignored_when_client_is_first(self):
        h = _holding(100_000, 90, rank=1, alternatives=[_option(80, 104_000)])
        assert holding_upside(h) == 0

    def test_never_negative(self):
        h = _holding(100_000, 50, alternatives=[_option(90, 97_000)])
        assert holding_upside(h) == 0

    def test_gross_mode_uses_gross_projection(self):
        h = _holding(100_000, 50, alternatives=[_option(90, 104_000, gross_potential=104_600)])
        assert holding_upside(h, gross=True) == 4_600

    def test_missing_projection_is_ignored(self):
        h = _holding(100_000, 50, alternatives=[_option(90, None)])
        assert holding_upside(h) == 0

    def test_other_horizon(self):
        h = _holding(100_000, 50, alternatives=[_option(90, 104_000, potential_3=115_000)])
        assert holding_upside(h, horizon=3) == 15_000

    def test_five_year_horizon(self):
        option = _option(90, 104_000)
        option["potential_amount_5"] = 131_000
        option["gross"]["potential_amount_5"] = 133_000
        h = _holding(100_000, 50, alternatives=[option])
        assert (holding_upside(h, horizon=5), holding_upside(h, horizon=5, gross=True)) == (31_000, 33_000)
        assert summarize_portfolio([h])["upside"]["gross"]["5"] == 33_000


class TestSummarizePortfolio:
    def test_score_is_weighted_by_money(self):
        holdings = [_holding(100_000, 80.0), _holding(300_000, 40.0)]
        summary = summarize_portfolio(holdings)
        assert summary["weighted_score"] == 50.0
        assert summary["total_amount"] == 400_000

    def test_ungraded_holdings_do_not_drag_the_score(self):
        holdings = [_holding(100_000, 80.0), _holding(100_000, 0)]
        summary = summarize_portfolio(holdings)
        assert summary["weighted_score"] == 80.0
        assert summary["coverage"] == 50.0

    def test_no_graded_holdings(self):
        summary = summarize_portfolio([_holding(100_000, 0)])
        assert summary["weighted_score"] is None
        assert summary["potential_score"] is None
        assert summary["coverage"] == 0.0

    def test_potential_score_moves_to_best_alternative(self):
        holdings = [
            _holding(100_000, 40.0, alternatives=[_option(90.0, 101_000)]),
            _holding(100_000, 95.0, rank=1, alternatives=[_option(70.0, 99_000)]),
        ]
        summary = summarize_portfolio(holdings)
        assert summary["weighted_score"] == 67.5
        assert summary["potential_score"] == 92.5

    def test_upside_sums_holdings_per_mode_and_horizon(self):
        holdings = [
            _holding(100_000, 50, alternatives=[_option(90, 104_000, gross_potential=105_000)]),
            _holding(50_000, 50, alternatives=[_option(90, 51_000, gross_potential=51_500)]),
        ]
        upside = summarize_portfolio(holdings)["upside"]
        assert upside["net"]["1"] == 5_000
        assert upside["gross"]["1"] == 6_500
        assert upside["net"]["3"] == 0

    def test_weighted_percentile(self):
        holdings = [_holding(100_000, 80.0, percentile=90), _holding(100_000, 40.0, percentile=30)]
        assert summarize_portfolio(holdings)["weighted_percentile"] == pytest.approx(60.0)

    def test_empty_portfolio(self):
        summary = summarize_portfolio([])
        assert summary["holdings_count"] == 0
        assert summary["weighted_score"] is None
