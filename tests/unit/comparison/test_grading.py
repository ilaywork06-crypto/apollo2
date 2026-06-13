"""Unit tests for src/comparison/grading.py"""

from src.comparison.grading import add_grade_and_sort, calculate_grade, get_top_3
from tests.conftest import make_fund, make_normalized_fund


class TestCalculateGrade:
    def _full_fund(self, v1=80.0, v3=70.0, v5=60.0, vs=90.0) -> dict:
        return make_normalized_fund(
            tsua_1_norm=v1, tsua_3_norm=v3, tsua_5_norm=v5, sharpe_norm=vs
        )

    def test_returns_weighted_sum(self):
        fund = self._full_fund(v1=100.0, v3=100.0, v5=100.0, vs=100.0)
        grade = calculate_grade(fund, 10, 20, 25, 45)
        assert grade == 100.0

    def test_returns_zero_when_all_normalized_are_zero(self):
        fund = make_normalized_fund(tsua_1_norm=0.0, tsua_3_norm=0.0, tsua_5_norm=0.0, sharpe_norm=0.0)
        assert calculate_grade(fund, 10, 20, 25, 45) == 0

    def test_returns_zero_when_weights_dont_sum_to_100(self):
        fund = self._full_fund()
        # weights sum = 10+20+25+40 = 95 != 100
        assert calculate_grade(fund, 10, 20, 25, 40) == 0

    def test_returns_zero_when_only_one_field_nonzero(self):
        fund = make_normalized_fund(tsua_1_norm=50.0, tsua_3_norm=0.0, tsua_5_norm=0.0, sharpe_norm=0.0)
        # Only weight_1=10 is active -> total_weight=10 != 100
        assert calculate_grade(fund, 10, 20, 25, 45) == 0

    def test_grade_rounded_to_two_decimals(self):
        fund = self._full_fund(v1=33.33, v3=33.33, v5=33.34, vs=33.33)
        grade = calculate_grade(fund, 10, 20, 25, 45)
        assert grade == round(grade, 2)

    def test_lower_performance_gives_lower_grade(self):
        high = self._full_fund(v1=90.0, v3=85.0, v5=80.0, vs=95.0)
        low = self._full_fund(v1=20.0, v3=15.0, v5=10.0, vs=25.0)
        assert calculate_grade(high, 10, 20, 25, 45) > calculate_grade(low, 10, 20, 25, 45)

    def test_sharpe_dominates_with_default_weights(self):
        # Sharpe has weight 45; push it to 100, everything else to 0
        fund_high_sharpe = make_normalized_fund(tsua_1_norm=80.0, tsua_3_norm=80.0, tsua_5_norm=80.0, sharpe_norm=100.0)
        fund_low_sharpe = make_normalized_fund(tsua_1_norm=80.0, tsua_3_norm=80.0, tsua_5_norm=80.0, sharpe_norm=0.0)
        # fund_low_sharpe's sharpe is 0 -> weight_sharp not counted -> total_weight = 55 != 100 -> grade = 0
        assert calculate_grade(fund_high_sharpe, 10, 20, 25, 45) > calculate_grade(fund_low_sharpe, 10, 20, 25, 45)


class TestAddGradeAndSort:
    def test_sorted_descending_by_grade(self):
        funds = [
            make_normalized_fund("low",  tsua_1_norm=10.0, tsua_3_norm=10.0, tsua_5_norm=10.0, sharpe_norm=10.0),
            make_normalized_fund("high", tsua_1_norm=90.0, tsua_3_norm=90.0, tsua_5_norm=90.0, sharpe_norm=90.0),
            make_normalized_fund("mid",  tsua_1_norm=50.0, tsua_3_norm=50.0, tsua_5_norm=50.0, sharpe_norm=50.0),
        ]
        result = add_grade_and_sort(funds, 10, 20, 25, 45)
        assert result[0]["ID"] == "high"
        assert result[1]["ID"] == "mid"
        assert result[2]["ID"] == "low"

    def test_grade_key_added_to_each_fund(self):
        funds = [make_normalized_fund("1")]
        result = add_grade_and_sort(funds, 10, 20, 25, 45)
        assert "grade" in result[0]

    def test_empty_list(self):
        assert add_grade_and_sort([], 10, 20, 25, 45) == []

    def test_single_fund(self):
        fund = make_normalized_fund("solo")
        result = add_grade_and_sort([fund], 10, 20, 25, 45)
        assert len(result) == 1
        assert "grade" in result[0]


class TestGetTop3:
    def test_returns_first_three(self):
        funds = [make_fund(str(i)) for i in range(5)]
        top = get_top_3(funds)
        assert len(top) == 3
        assert top[0]["ID"] == "0"

    def test_returns_all_when_fewer_than_three(self):
        funds = [make_fund("1"), make_fund("2")]
        assert len(get_top_3(funds)) == 2

    def test_returns_empty_for_empty_list(self):
        assert get_top_3([]) == []

    def test_exactly_three(self):
        funds = [make_fund(str(i)) for i in range(3)]
        assert len(get_top_3(funds)) == 3
