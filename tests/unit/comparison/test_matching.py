"""Unit tests for src/comparison/matching.py"""

from src.comparison.matching import find_matching_funds, get_funds_by_risk_level
from tests.conftest import make_fund


class TestFindMatchingFunds:
    def test_all_match(self):
        funds = [make_fund("1"), make_fund("2"), make_fund("3")]
        mislaka = [
            {"GEMELNET_ID": "1", "TOTAL-CHISACHON-MTZBR": 50000},
            {"GEMELNET_ID": "2", "TOTAL-CHISACHON-MTZBR": 80000},
        ]
        result = find_matching_funds(mislaka, funds)
        assert len(result) == 2
        ids = {m["GEMELNET_ID"] for m, _ in result}
        assert ids == {"1", "2"}

    def test_no_match_returns_empty(self):
        funds = [make_fund("999")]
        mislaka = [{"GEMELNET_ID": "1"}]
        assert find_matching_funds(mislaka, funds) == []

    def test_partial_match(self):
        funds = [make_fund("1"), make_fund("3")]
        mislaka = [
            {"GEMELNET_ID": "1"},
            {"GEMELNET_ID": "2"},
            {"GEMELNET_ID": "3"},
        ]
        result = find_matching_funds(mislaka, funds)
        assert len(result) == 2

    def test_empty_mislaka(self):
        funds = [make_fund("1")]
        assert find_matching_funds([], funds) == []

    def test_empty_funds(self):
        mislaka = [{"GEMELNET_ID": "1"}]
        assert find_matching_funds(mislaka, []) == []

    def test_result_is_tuple_of_mislaka_and_fund(self):
        fund = make_fund("42")
        mislaka = [{"GEMELNET_ID": "42", "extra": "data"}]
        pairs = find_matching_funds(mislaka, [fund])
        assert len(pairs) == 1
        m, f = pairs[0]
        assert m["GEMELNET_ID"] == "42"
        assert f["ID"] == "42"

    def test_duplicate_fund_ids_not_duplicated(self):
        funds = [make_fund("1"), make_fund("1")]  # duplicate fund
        mislaka = [{"GEMELNET_ID": "1"}]
        result = find_matching_funds(mislaka, funds)
        # dict comprehension keeps last; should still return exactly 1 pair
        assert len(result) == 1


class TestGetFundsByRiskLevel:
    def test_filters_medium(self):
        funds = [
            make_fund("1", risk_level="low"),
            make_fund("2", risk_level="medium"),
            make_fund("3", risk_level="high"),
            make_fund("4", risk_level="medium"),
        ]
        result = get_funds_by_risk_level(funds, "medium")
        assert len(result) == 2
        assert all(f["risk_level"] == "medium" for f in result)

    def test_empty_list_returns_empty(self):
        assert get_funds_by_risk_level([], "high") == []

    def test_no_match_returns_empty(self):
        funds = [make_fund("1", risk_level="low")]
        assert get_funds_by_risk_level(funds, "high") == []

    def test_all_same_risk(self):
        funds = [make_fund(str(i), risk_level="high") for i in range(5)]
        assert len(get_funds_by_risk_level(funds, "high")) == 5

    def test_invalid_risk_level_matches_invalid_funds(self):
        funds = [make_fund("1", risk_level="invalid"), make_fund("2", risk_level="low")]
        result = get_funds_by_risk_level(funds, "invalid")
        assert len(result) == 1
