"""Properties of the Israel / abroad equity split and the geography filter."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.comparison.filters import filter_by_israel_equity_share
from src.comparison.risk_classifier import RiskClassifier, split_equity_exposure
from tests.conftest import make_fund
from tests.strategies import fund_lists

hundredths = st.integers(0, 13_000).map(lambda n: n / 100)  # 0.00 … 130.00, like the risk map
share_bounds = st.tuples(st.integers(0, 100), st.integers(0, 100)).map(sorted)


class TestSplitProperties:
    @given(hundredths, hundredths)
    def test_israeli_part_is_equity_minus_foreign_within_zero_and_equity(self, equity, foreign):
        israel, _ = split_equity_exposure(equity, foreign)
        assert israel == pytest.approx(min(max(equity - foreign, 0.0), equity), abs=0.005)
        assert 0.0 <= israel <= equity

    @given(hundredths.filter(lambda e: e > 0), hundredths)
    def test_share_is_the_israeli_part_of_the_equity(self, equity, foreign):
        israel, share = split_equity_exposure(equity, foreign)
        assert 0.0 <= share <= 100.0
        assert share == pytest.approx(min(max(equity - foreign, 0.0), equity) / equity * 100, abs=0.05)

    @given(hundredths.filter(lambda e: e > 0), hundredths, hundredths)
    def test_more_foreign_exposure_never_means_more_israel(self, equity, a, b):
        low, high = sorted((a, b))
        assert split_equity_exposure(equity, high)[1] <= split_equity_exposure(equity, low)[1]

    @given(hundredths.filter(lambda e: e > 0))
    def test_no_foreign_exposure_is_all_israel(self, equity):
        assert split_equity_exposure(equity, 0.0) == (round(equity, 2), 100.0)

    @given(hundredths)
    def test_unknown_data_gives_no_split(self, value):
        assert split_equity_exposure(None, value) == (None, None)
        assert split_equity_exposure(value, None) == (None, None)


class TestSplitEdges:
    def test_fraction_of_a_percent_above_zero_is_kept(self):
        # Floored at 0, not at 1
        assert split_equity_exposure(50.0, 49.5) == (0.5, 1.0)

    def test_tiny_equity_still_has_a_share(self):
        assert split_equity_exposure(0.5, 0.0) == (0.5, 100.0)

    def test_rounding(self):
        assert split_equity_exposure(33.333, 0.001) == (33.33, 100.0)
        assert split_equity_exposure(30.0, 20.0) == (10.0, 33.3)

    def test_classifier_requires_a_source(self):
        with pytest.raises(ValueError, match="requires either 'risks' or 'path'"):
            RiskClassifier()


class TestGeographyFilterProperties:
    @given(fund_lists(max_size=15), share_bounds)
    def test_returns_exactly_the_funds_inside_the_range(self, funds, bounds):
        low, high = bounds
        result = filter_by_israel_equity_share(funds, low, high)
        if low <= 0 and high >= 100:
            assert result == funds  # no preference: nothing is dropped, not even unknown shares
            return
        expected = [
            f for f in funds
            if f["israel_equity_share"] is not None and low <= f["israel_equity_share"] <= high
        ]
        assert result == expected

    @given(fund_lists(max_size=15), share_bounds, share_bounds)
    def test_widening_the_range_never_drops_a_fund(self, funds, a, b):
        narrow = (max(a[0], b[0]), min(a[1], b[1]))
        wide = (min(a[0], b[0]), max(a[1], b[1]))
        if narrow[0] > narrow[1]:
            return
        kept_narrow = {f["ID"] for f in filter_by_israel_equity_share(funds, *narrow)}
        kept_wide = {f["ID"] for f in filter_by_israel_equity_share(funds, *wide)}
        assert kept_narrow <= kept_wide


class TestGeographyFilterEdges:
    def _fund(self, fund_id, equity, foreign):
        return make_fund(fund_id, equity_exposure=equity, foreign_exposure=foreign)

    def test_defaults_mean_no_preference(self):
        funds = [self._fund("a", 100.0, 99.5), self._fund("b", 50.0, None)]
        assert filter_by_israel_equity_share(funds) == funds

    def test_a_one_percent_floor_drops_a_half_percent_fund(self):
        funds = [self._fund("half", 100.0, 99.5), self._fund("five", 100.0, 95.0)]
        assert [f["ID"] for f in filter_by_israel_equity_share(funds, 1, 100)] == ["five"]

    def test_bounds_are_inclusive(self):
        funds = [self._fund("sixty", 100.0, 40.0), self._fund("forty", 100.0, 60.0)]
        assert [f["ID"] for f in filter_by_israel_equity_share(funds, 40, 60)] == ["sixty", "forty"]
