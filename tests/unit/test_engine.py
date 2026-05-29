"""Unit tests for src/core/engine.py pure functions (no file I/O)."""

import copy

import pytest

from src.core.engine import (
    add_grade_and_sort,
    apply_dmey_nihul,
    calculate_grade,
    calculate_potential_amount,
    find_matching_funds,
    get_client_ranking,
    get_funds_by_risk_level,
    get_top_3,
    normalize_data,
)
from tests.conftest import make_fund, make_normalized_fund


# ---------------------------------------------------------------------------
# find_matching_funds
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# get_funds_by_risk_level
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# apply_dmey_nihul
# ---------------------------------------------------------------------------


class TestApplyDmeyNihul:
    def test_subtracts_fee_from_positive_returns(self):
        funds = [make_fund("1", tsua_1=10.0, tsua_3=8.0, tsua_5=7.0)]
        result = apply_dmey_nihul(funds, 0.5)
        f = result[0]
        assert abs(f["tsua_mitztaberet_letkufa"] - 9.5) < 1e-9
        assert abs(f["tsua_3"] - 7.5) < 1e-9
        assert abs(f["tsua_5"] - 6.5) < 1e-9

    def test_does_not_modify_zero_returns(self):
        fund = make_fund("1")
        fund["tsua_mitztaberet_letkufa"] = 0.0
        fund["tsua_3"] = 0.0
        fund["tsua_5"] = 0.0
        result = apply_dmey_nihul([fund], 0.5)
        assert result[0]["tsua_mitztaberet_letkufa"] == 0.0
        assert result[0]["tsua_3"] == 0.0
        assert result[0]["tsua_5"] == 0.0

    def test_does_not_modify_negative_returns(self):
        fund = make_fund("1")
        fund["tsua_mitztaberet_letkufa"] = -2.0
        fund["tsua_3"] = -1.0
        fund["tsua_5"] = -0.5
        result = apply_dmey_nihul([fund], 0.5)
        assert result[0]["tsua_mitztaberet_letkufa"] == -2.0
        assert result[0]["tsua_3"] == -1.0
        assert result[0]["tsua_5"] == -0.5

    def test_zero_fee_does_not_change_values(self):
        funds = [make_fund("1", tsua_1=10.0, tsua_3=8.0, tsua_5=6.0)]
        original = copy.deepcopy(funds)
        apply_dmey_nihul(funds, 0.0)
        assert funds[0]["tsua_mitztaberet_letkufa"] == original[0]["tsua_mitztaberet_letkufa"]

    def test_modifies_in_place_and_returns_same_list(self):
        funds = [make_fund("1", tsua_1=10.0)]
        result = apply_dmey_nihul(funds, 1.0)
        assert result is funds

    def test_large_fee_can_make_return_negative(self):
        funds = [make_fund("1", tsua_1=3.0)]
        result = apply_dmey_nihul(funds, 5.0)
        assert result[0]["tsua_mitztaberet_letkufa"] == pytest.approx(-2.0)

    def test_multiple_funds(self):
        funds = [
            make_fund("1", tsua_1=10.0, tsua_3=8.0, tsua_5=6.0),
            make_fund("2", tsua_1=20.0, tsua_3=15.0, tsua_5=12.0),
        ]
        result = apply_dmey_nihul(funds, 1.0)
        assert result[0]["tsua_mitztaberet_letkufa"] == pytest.approx(9.0)
        assert result[1]["tsua_mitztaberet_letkufa"] == pytest.approx(19.0)


# ---------------------------------------------------------------------------
# normalize_data
# ---------------------------------------------------------------------------


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
        # Only one non-zero value → min == max → all get 0.0
        funds = [make_fund("1", tsua_1=10.0, tsua_3=8.0, tsua_5=6.0, sharpe=1.5)]
        normalize_data(funds)
        assert funds[0]["tsua_mitztaberet_letkufa_normalized"] == 0.0

    def test_fund_with_zero_tsua_not_included_in_range(self):
        f1 = make_fund("1", tsua_1=0.0)   # zero → excluded from min/max
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


# ---------------------------------------------------------------------------
# calculate_grade
# ---------------------------------------------------------------------------


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
        # Only weight_1=10 is active → total_weight=10 != 100
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
        # fund_low_sharpe's sharpe is 0 → weight_sharp not counted → total_weight = 55 != 100 → grade = 0
        assert calculate_grade(fund_high_sharpe, 10, 20, 25, 45) > calculate_grade(fund_low_sharpe, 10, 20, 25, 45)


# ---------------------------------------------------------------------------
# add_grade_and_sort
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# get_top_3
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# get_client_ranking
# ---------------------------------------------------------------------------


class TestGetClientRanking:
    def _sorted_funds(self, ids):
        return [make_fund(fid) for fid in ids]

    def test_finds_rank_at_first_position(self):
        funds = self._sorted_funds(["A", "B", "C"])
        rank, total = get_client_ranking(funds, "A")
        assert rank == 1
        assert total == 3

    def test_finds_rank_at_last_position(self):
        funds = self._sorted_funds(["A", "B", "C"])
        rank, total = get_client_ranking(funds, "C")
        assert rank == 3
        assert total == 3

    def test_not_found_returns_none(self):
        funds = self._sorted_funds(["A", "B"])
        rank, total = get_client_ranking(funds, "Z")
        assert rank is None
        assert total == 2

    def test_empty_list(self):
        rank, total = get_client_ranking([], "X")
        assert rank is None
        assert total == 0

    def test_total_reflects_full_list_length(self):
        funds = self._sorted_funds(["A", "B", "C", "D", "E"])
        _, total = get_client_ranking(funds, "C")
        assert total == 5


# ---------------------------------------------------------------------------
# calculate_potential_amount
# ---------------------------------------------------------------------------


class TestCalculatePotentialAmount:
    def test_better_fund_gives_more_money(self):
        current = make_fund("c", tsua_1=5.0)
        better = make_fund("b", tsua_1=15.0)
        result = calculate_potential_amount(100_000.0, current, better, "tsua_mitztaberet_letkufa", 1)
        assert result > 100_000.0

    def test_same_return_gives_same_amount(self):
        fund = make_fund("f", tsua_1=10.0)
        result = calculate_potential_amount(100_000.0, fund, fund, "tsua_mitztaberet_letkufa", 1)
        assert result == pytest.approx(100_000.0, rel=1e-6)

    def test_worse_fund_gives_less_money(self):
        current = make_fund("c", tsua_1=15.0)
        worse = make_fund("w", tsua_1=5.0)
        result = calculate_potential_amount(100_000.0, current, worse, "tsua_mitztaberet_letkufa", 1)
        assert result < 100_000.0

    def test_compounding_over_multiple_years(self):
        current = make_fund("c", tsua_5=5.0)
        better = make_fund("b", tsua_5=10.0)
        one_year = calculate_potential_amount(100_000.0, current, better, "tsua_5", 1)
        five_year = calculate_potential_amount(100_000.0, current, better, "tsua_5", 5)
        assert five_year > one_year

    def test_result_rounded_to_two_decimals(self):
        current = make_fund("c", tsua_1=7.0)
        better = make_fund("b", tsua_1=13.0)
        result = calculate_potential_amount(100_000.0, current, better)
        assert result == round(result, 2)

    def test_zero_current_return_uses_denominator_of_one(self):
        current = make_fund("c", tsua_1=0.0)
        better = make_fund("b", tsua_1=10.0)
        result = calculate_potential_amount(100_000.0, current, better, "tsua_mitztaberet_letkufa", 1)
        expected = round(100_000.0 * 1.10 / 1.0, 2)
        assert result == expected

    def test_large_balance(self):
        current = make_fund("c", tsua_1=5.0)
        better = make_fund("b", tsua_1=8.0)
        result = calculate_potential_amount(10_000_000.0, current, better)
        assert result > 10_000_000.0


# ---------------------------------------------------------------------------
# calculate_potential_amount — exact numerical verification
#
# Question answered: "If I had been in the better fund for the past N years,
# how much money would I have TODAY?"
#
# Derivation:
#   starting_balance = current_amount / (1 + current_return%)^N   (back-calculate)
#   today_in_better  = starting_balance × (1 + better_return%)^N
#                    = current_amount × (1 + better%)^N / (1 + current%)^N
# ---------------------------------------------------------------------------


class TestCalculatePotentialAmountExact:
    """Verify the 'how much would I have today' formula for 1, 3, and 5 year horizons."""

    def _expected(self, amount, current_return, better_return, years):
        """What I'd have today if I'd been in the better fund for the past N years."""
        return round(
            amount * (1 + better_return / 100) ** years / (1 + current_return / 100) ** years,
            2,
        )

    # ── 1-year (tsua_mitztaberet_letkufa) ──────────────────────────────────

    def test_exact_value_1yr_simple(self):
        current = make_fund("c", tsua_1=5.0)
        better = make_fund("b", tsua_1=10.0)
        result = calculate_potential_amount(100_000.0, current, better, "tsua_mitztaberet_letkufa", 1)
        # 100_000 * 1.10 / 1.05 = 104_761.90...
        expected = self._expected(100_000.0, 5.0, 10.0, 1)
        assert result == expected

    def test_exact_value_1yr_high_current_return(self):
        current = make_fund("c", tsua_1=20.0)
        better = make_fund("b", tsua_1=25.0)
        result = calculate_potential_amount(200_000.0, current, better, "tsua_mitztaberet_letkufa", 1)
        expected = self._expected(200_000.0, 20.0, 25.0, 1)
        assert result == expected

    def test_exact_value_1yr_fractional_returns(self):
        current = make_fund("c", tsua_1=7.5)
        better = make_fund("b", tsua_1=13.25)
        result = calculate_potential_amount(50_000.0, current, better, "tsua_mitztaberet_letkufa", 1)
        expected = self._expected(50_000.0, 7.5, 13.25, 1)
        assert result == expected

    # ── 3-year (tsua_3) ────────────────────────────────────────────────────

    def test_exact_value_3yr(self):
        # "Had I been in the better fund for the past 3 years, what would I have today?"
        current = make_fund("c", tsua_3=5.0)
        better = make_fund("b", tsua_3=10.0)
        result = calculate_potential_amount(100_000.0, current, better, "tsua_3", 3)
        # back-calculate starting balance: 100_000 / 1.05^3, grow at 10%: × 1.10^3
        expected = self._expected(100_000.0, 5.0, 10.0, 3)
        assert result == expected

    def test_exact_value_3yr_large_balance(self):
        current = make_fund("c", tsua_3=6.0)
        better = make_fund("b", tsua_3=12.0)
        result = calculate_potential_amount(500_000.0, current, better, "tsua_3", 3)
        expected = self._expected(500_000.0, 6.0, 12.0, 3)
        assert result == expected

    def test_exact_value_3yr_small_spread(self):
        # Only 0.5 % difference in annualised return
        current = make_fund("c", tsua_3=8.0)
        better = make_fund("b", tsua_3=8.5)
        result = calculate_potential_amount(100_000.0, current, better, "tsua_3", 3)
        expected = self._expected(100_000.0, 8.0, 8.5, 3)
        assert result == expected

    def test_3yr_is_greater_than_1yr_for_same_positive_spread(self):
        # Compounding means the 3yr gain is larger than 3 × the 1yr gain
        current = make_fund("c", tsua_1=5.0, tsua_3=5.0)
        better = make_fund("b", tsua_1=10.0, tsua_3=10.0)
        one_yr = calculate_potential_amount(100_000.0, current, better, "tsua_mitztaberet_letkufa", 1)
        three_yr = calculate_potential_amount(100_000.0, current, better, "tsua_3", 3)
        gain_1 = one_yr - 100_000.0
        gain_3 = three_yr - 100_000.0
        assert gain_3 > 3 * gain_1

    # ── 5-year (tsua_5) ────────────────────────────────────────────────────

    def test_exact_value_5yr(self):
        # "Had I been in the better fund for the past 5 years, what would I have today?"
        current = make_fund("c", tsua_5=5.0)
        better = make_fund("b", tsua_5=10.0)
        result = calculate_potential_amount(100_000.0, current, better, "tsua_5", 5)
        # back-calculate starting balance: 100_000 / 1.05^5, grow at 10%: × 1.10^5
        expected = self._expected(100_000.0, 5.0, 10.0, 5)
        assert result == expected

    def test_exact_value_5yr_large_balance(self):
        current = make_fund("c", tsua_5=4.0)
        better = make_fund("b", tsua_5=9.0)
        result = calculate_potential_amount(1_000_000.0, current, better, "tsua_5", 5)
        expected = self._expected(1_000_000.0, 4.0, 9.0, 5)
        assert result == expected

    def test_exact_value_5yr_fractional(self):
        current = make_fund("c", tsua_5=6.75)
        better = make_fund("b", tsua_5=11.33)
        result = calculate_potential_amount(75_000.0, current, better, "tsua_5", 5)
        expected = self._expected(75_000.0, 6.75, 11.33, 5)
        assert result == expected

    def test_5yr_is_greater_than_3yr_for_same_positive_spread(self):
        current = make_fund("c", tsua_3=5.0, tsua_5=5.0)
        better = make_fund("b", tsua_3=10.0, tsua_5=10.0)
        three_yr = calculate_potential_amount(100_000.0, current, better, "tsua_3", 3)
        five_yr = calculate_potential_amount(100_000.0, current, better, "tsua_5", 5)
        assert five_yr > three_yr

    # ── Rounding ───────────────────────────────────────────────────────────

    def test_result_rounded_to_exactly_two_decimal_places(self):
        current = make_fund("c", tsua_5=7.333)
        better = make_fund("b", tsua_5=12.777)
        result = calculate_potential_amount(123_456.78, current, better, "tsua_5", 5)
        # Verify the result has at most 2 decimal places
        assert result == round(result, 2)
        # And matches the formula exactly
        expected = self._expected(123_456.78, 7.333, 12.777, 5)
        assert result == expected

    # ── Cross-horizon consistency ──────────────────────────────────────────

    def test_1yr_3yr_5yr_all_match_formula(self):
        """One omnibus test: verify all three horizons against the formula simultaneously."""
        amount = 150_000.0
        current = make_fund("c", tsua_1=6.0, tsua_3=6.0, tsua_5=6.0)
        better = make_fund("b", tsua_1=11.0, tsua_3=11.0, tsua_5=11.0)

        r1 = calculate_potential_amount(amount, current, better, "tsua_mitztaberet_letkufa", 1)
        r3 = calculate_potential_amount(amount, current, better, "tsua_3", 3)
        r5 = calculate_potential_amount(amount, current, better, "tsua_5", 5)

        assert r1 == self._expected(amount, 6.0, 11.0, 1)
        assert r3 == self._expected(amount, 6.0, 11.0, 3)
        assert r5 == self._expected(amount, 6.0, 11.0, 5)
        # Ordering must hold
        assert r1 < r3 < r5
