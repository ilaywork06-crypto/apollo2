"""Unit tests for src/comparison/filters.py"""

from src.comparison.filters import filter_by_israel_equity_share, remove_bad_hevrot
from tests.conftest import make_fund


class TestRemoveBadHevrot:
    def test_removes_specified_companies(self):
        funds = [
            make_fund("1", hevra="Good Co"),
            make_fund("2", hevra="Bad Co"),
            make_fund("3", hevra="Also Bad"),
        ]
        result = remove_bad_hevrot(funds, ["Bad Co", "Also Bad"])
        assert len(result) == 1
        assert result[0]["hevra"] == "Good Co"

    def test_empty_blacklist_returns_all(self):
        funds = [make_fund(str(i)) for i in range(3)]
        assert remove_bad_hevrot(funds, []) == funds

    def test_empty_funds_returns_empty(self):
        assert remove_bad_hevrot([], ["Bad Co"]) == []


class TestFilterByIsraelEquityShare:
    def _funds(self):
        return [
            make_fund("il", equity_exposure=100.0, foreign_exposure=0.0),     # 100% Israel
            make_fund("mix", equity_exposure=100.0, foreign_exposure=60.0),   # 40% Israel
            make_fund("abroad", equity_exposure=100.0, foreign_exposure=100.0),  # 0% Israel
            make_fund("unknown", equity_exposure=100.0, foreign_exposure=None),
        ]

    def test_full_range_is_no_filter(self):
        funds = self._funds()
        assert filter_by_israel_equity_share(funds, 0, 100) is funds

    def test_israel_heavy_range(self):
        result = filter_by_israel_equity_share(self._funds(), 60, 100)
        assert [f["ID"] for f in result] == ["il"]

    def test_abroad_heavy_range(self):
        result = filter_by_israel_equity_share(self._funds(), 0, 40)
        assert [f["ID"] for f in result] == ["mix", "abroad"]

    def test_unknown_share_excluded_when_filtering(self):
        result = filter_by_israel_equity_share(self._funds(), 10, 100)
        assert "unknown" not in [f["ID"] for f in result]
