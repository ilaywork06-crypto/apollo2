"""Unit tests for src/comparison/normalization.py"""

from src.comparison.normalization import normalize_data
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
