"""Unit tests for src/comparison/normalization.py"""

import pytest

from src.comparison.normalization import normalize_data, normalize_liquidity
from tests.conftest import make_fund


class TestNormalizeData:
    def _three_funds(self):
        f1 = make_fund("1", tsua_1=10.0, tsua_3=8.0, tsua_5=6.0, sharpe=1.0)
        f2 = make_fund("2", tsua_1=20.0, tsua_3=16.0, tsua_5=14.0, sharpe=2.0)
        f3 = make_fund("3", tsua_1=30.0, tsua_3=24.0, tsua_5=22.0, sharpe=3.0)
        return [f1, f2, f3]

    def test_min_value_gets_zero(self):
        funds = self._three_funds()
        normalize_data(funds)
        assert funds[0]["tsua_mitztaberet_letkufa_normalized"] == 0.0

    def test_max_value_gets_100(self):
        funds = self._three_funds()
        normalize_data(funds)
        assert funds[2]["tsua_mitztaberet_letkufa_normalized"] == 100.0

    def test_middle_value_gets_50(self):
        funds = self._three_funds()
        normalize_data(funds)
        assert abs(funds[1]["tsua_mitztaberet_letkufa_normalized"] - 50.0) < 1e-9

    def test_all_normalized_fields_added(self):
        funds = self._three_funds()
        normalize_data(funds)
        for fund in funds:
            assert "tsua_mitztaberet_letkufa_normalized" in fund
            assert "tsua_3_normalized" in fund
            assert "tsua_5_normalized" in fund
            assert "sharp_ribit_hasarot_sikun_normalized" in fund

    def test_all_zero_fields_give_zero_normalized(self):
        f1 = make_fund("1", tsua_1=0.0, tsua_3=0.0, tsua_5=0.0, sharpe=0.0)
        f2 = make_fund("2", tsua_1=0.0, tsua_3=0.0, tsua_5=0.0, sharpe=0.0)
        normalize_data([f1, f2])
        assert f1["tsua_mitztaberet_letkufa_normalized"] == 0.0
        assert f2["tsua_mitztaberet_letkufa_normalized"] == 0.0

    def test_single_nonzero_fund_gets_zero_normalized(self):
        # Only one non-zero value -> min == max -> all get 0.0
        funds = [make_fund("1", tsua_1=10.0, tsua_3=8.0, tsua_5=6.0, sharpe=1.5)]
        normalize_data(funds)
        assert funds[0]["tsua_mitztaberet_letkufa_normalized"] == 0.0

    def test_fund_with_zero_tsua_not_included_in_range(self):
        f1 = make_fund("1", tsua_1=0.0)   # zero -> excluded from min/max
        f2 = make_fund("2", tsua_1=10.0)
        f3 = make_fund("3", tsua_1=20.0)
        normalize_data([f1, f2, f3])
        assert f1["tsua_mitztaberet_letkufa_normalized"] == 0.0
        assert f2["tsua_mitztaberet_letkufa_normalized"] == 0.0   # min among non-zeros
        assert f3["tsua_mitztaberet_letkufa_normalized"] == 100.0

    def test_modifies_in_place(self):
        funds = self._three_funds()
        original = funds
        normalize_data(funds)
        assert funds is original


class TestNormalizeLiquidity:
    def _funds(self, *values):
        return [make_fund(str(i), liquidity_index=v) for i, v in enumerate(values)]

    def test_highest_gets_100_and_lowest_gets_0(self):
        funds = self._funds(12.0, -30.0, 4.0)
        normalize_liquidity(funds)
        assert funds[0]["liquidity_index_normalized"] == 100.0
        assert funds[1]["liquidity_index_normalized"] == 0.0

    def test_ranks_are_evenly_spaced(self):
        funds = self._funds(-50.0, -1.0, 2.0, 400.0, 9.0)
        normalize_liquidity(funds)
        assert [f["liquidity_index_normalized"] for f in funds] == [0.0, 25.0, 50.0, 100.0, 75.0]

    def test_outlier_does_not_squash_the_rest(self):
        # Percentile rank is robust: one extreme outflow doesn't flatten the others
        funds = self._funds(-1974.0, 1.0, 2.0)
        normalize_liquidity(funds)
        assert funds[1]["liquidity_index_normalized"] == 50.0

    def test_ties_share_their_average_rank(self):
        funds = self._funds(1.0, 5.0, 5.0, 9.0)
        normalize_liquidity(funds)
        assert funds[1]["liquidity_index_normalized"] == pytest.approx(50.0)
        assert funds[2]["liquidity_index_normalized"] == pytest.approx(50.0)

    def test_missing_data_is_excluded_from_ranking(self):
        funds = self._funds(None, -3.0, 7.0)
        normalize_liquidity(funds)
        assert funds[0]["liquidity_index_normalized"] == 0.0
        assert funds[1]["liquidity_index_normalized"] == 0.0
        assert funds[2]["liquidity_index_normalized"] == 100.0

    def test_single_fund_gets_neutral_score(self):
        funds = self._funds(3.0)
        normalize_liquidity(funds)
        assert funds[0]["liquidity_index_normalized"] == 50.0

    def test_zero_is_real_data(self):
        funds = self._funds(0.0, 5.0)
        normalize_liquidity(funds)
        assert funds[0]["liquidity_index_normalized"] == 0.0
        assert funds[1]["liquidity_index_normalized"] == 100.0

    def test_normalize_data_includes_liquidity(self):
        funds = self._funds(1.0, 2.0)
        normalize_data(funds)
        assert funds[1]["liquidity_index_normalized"] == 100.0
