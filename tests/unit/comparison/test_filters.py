"""Unit tests for src/comparison/filters.py"""

from src.comparison.filters import remove_bad_hevrot
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
