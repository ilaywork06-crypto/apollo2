"""Unit tests for src/comparison/projections.py"""

import pytest

from src.comparison.projections import calculate_potential_amount
from tests.conftest import make_fund


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
# calculate_potential_amount - exact numerical verification
#
# Question answered: "If I had been in the better fund for the past N years,
# how much money would I have TODAY?"
#
# Derivation:
#   starting_balance = current_amount / (1 + current_return%)^N   (back-calculate)
#   today_in_better  = starting_balance x (1 + better_return%)^N
#                    = current_amount x (1 + better%)^N / (1 + current%)^N
# ---------------------------------------------------------------------------


class TestCalculatePotentialAmountExact:
    """Verify the 'how much would I have today' formula for 1, 3, and 5 year horizons."""

    def _expected(self, amount, current_return, better_return, years):
        """What I'd have today if I'd been in the better fund for the past N years."""
        return round(
            amount * (1 + better_return / 100) ** years / (1 + current_return / 100) ** years,
            2,
        )

    # 1-year (tsua_mitztaberet_letkufa)

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

    # 3-year (tsua_3)

    def test_exact_value_3yr(self):
        # "Had I been in the better fund for the past 3 years, what would I have today?"
        current = make_fund("c", tsua_3=5.0)
        better = make_fund("b", tsua_3=10.0)
        result = calculate_potential_amount(100_000.0, current, better, "tsua_3", 3)
        # back-calculate starting balance: 100_000 / 1.05^3, grow at 10%: x 1.10^3
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
        # Compounding means the 3yr gain is larger than 3 x the 1yr gain
        current = make_fund("c", tsua_1=5.0, tsua_3=5.0)
        better = make_fund("b", tsua_1=10.0, tsua_3=10.0)
        one_yr = calculate_potential_amount(100_000.0, current, better, "tsua_mitztaberet_letkufa", 1)
        three_yr = calculate_potential_amount(100_000.0, current, better, "tsua_3", 3)
        gain_1 = one_yr - 100_000.0
        gain_3 = three_yr - 100_000.0
        assert gain_3 > 3 * gain_1

    # 5-year (tsua_5)

    def test_exact_value_5yr(self):
        # "Had I been in the better fund for the past 5 years, what would I have today?"
        current = make_fund("c", tsua_5=5.0)
        better = make_fund("b", tsua_5=10.0)
        result = calculate_potential_amount(100_000.0, current, better, "tsua_5", 5)
        # back-calculate starting balance: 100_000 / 1.05^5, grow at 10%: x 1.10^5
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

    # Rounding

    def test_result_rounded_to_exactly_two_decimal_places(self):
        current = make_fund("c", tsua_5=7.333)
        better = make_fund("b", tsua_5=12.777)
        result = calculate_potential_amount(123_456.78, current, better, "tsua_5", 5)
        # Verify the result has at most 2 decimal places
        assert result == round(result, 2)
        # And matches the formula exactly
        expected = self._expected(123_456.78, 7.333, 12.777, 5)
        assert result == expected

    # Cross-horizon consistency

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
