"""Property-based tests for AmoScore: normalisation, liquidity ranking, grading, pool building.

Each test states an invariant that must hold for every generated fund pool,
not just a handful of hand-picked examples.
"""

import copy

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from src.comparison.fees import RETURN_FIELDS, apply_dmey_nihul
from src.comparison.grading import add_grade_and_sort, calculate_grade
from src.comparison.normalization import (
    LIQUIDITY_FIELD,
    MIN_MAX_FIELDS,
    has_metric,
    normalize_data,
    normalize_liquidity,
)
from src.comparison.pool import build_graded_pool
from tests.strategies import fees, fund_lists

# Four cut points on 0..100 split it into five weights that always sum to 100 (no filtering)
weights_summing_to_100 = st.lists(st.integers(0, 100), min_size=4, max_size=4).map(sorted).map(
    lambda c: (c[0], c[1] - c[0], c[2] - c[1], c[3] - c[2], 100 - c[3])
)


# ---------------------------------------------------------------------------
# Min-max normalisation (returns and Sharpe)
# ---------------------------------------------------------------------------


class TestMinMaxNormalisation:
    @given(fund_lists())
    def test_every_score_is_between_0_and_100(self, funds):
        normalize_data(funds)
        for fund in funds:
            for field in MIN_MAX_FIELDS:
                assert 0.0 <= fund[field + "_normalized"] <= 100.0

    @given(fund_lists(min_size=2))
    def test_best_gets_100_and_worst_gets_0(self, funds):
        normalize_data(funds)
        for field in MIN_MAX_FIELDS:
            values = [f[field] for f in funds if has_metric(f, field)]
            assume(len(set(values)) >= 2)
            best = max(funds, key=lambda f: f[field] if has_metric(f, field) else float("-inf"))
            worst = min(funds, key=lambda f: f[field] if has_metric(f, field) else float("inf"))
            assert best[field + "_normalized"] == 100.0
            assert worst[field + "_normalized"] == 0.0

    @given(fund_lists(min_size=2))
    def test_order_is_preserved(self, funds):
        normalize_data(funds)
        for field in MIN_MAX_FIELDS:
            present = [f for f in funds if has_metric(f, field)]
            for a in present:
                for b in present:
                    if a[field] < b[field]:
                        assert a[field + "_normalized"] <= b[field + "_normalized"]

    @given(fund_lists(), st.data())
    def test_missing_data_scores_zero_and_does_not_move_the_range(self, funds, data):
        victim = data.draw(st.sampled_from(funds))
        field = data.draw(st.sampled_from(MIN_MAX_FIELDS))
        others = copy.deepcopy([f for f in funds if f is not victim])
        victim[field] = 0.0  # the parser's "no data" marker
        normalize_data(funds)
        normalize_data(others)
        assert victim[field + "_normalized"] == 0.0
        by_id = {f["ID"]: f for f in funds}
        for other in others:
            assert by_id[other["ID"]][field + "_normalized"] == other[field + "_normalized"]


# ---------------------------------------------------------------------------
# Liquidity percentile rank
# ---------------------------------------------------------------------------


class TestLiquidityPercentile:
    @given(fund_lists())
    def test_scores_are_between_0_and_100(self, funds):
        normalize_liquidity(funds)
        assert all(0.0 <= f["liquidity_index_normalized"] <= 100.0 for f in funds)

    @given(fund_lists(min_size=2))
    def test_highest_net_inflow_gets_100_and_biggest_outflow_gets_0(self, funds):
        assume(len({f[LIQUIDITY_FIELD] for f in funds}) >= 2)
        normalize_liquidity(funds)
        top = max(f[LIQUIDITY_FIELD] for f in funds)
        bottom = min(f[LIQUIDITY_FIELD] for f in funds)
        for fund in funds:
            if fund[LIQUIDITY_FIELD] == top:
                assert fund["liquidity_index_normalized"] == 100.0
            if fund[LIQUIDITY_FIELD] == bottom:
                assert fund["liquidity_index_normalized"] == 0.0

    @given(fund_lists(min_size=2))
    def test_more_inflow_never_ranks_lower_and_ties_rank_equal(self, funds):
        normalize_liquidity(funds)
        for a in funds:
            for b in funds:
                if a[LIQUIDITY_FIELD] < b[LIQUIDITY_FIELD]:
                    assert a["liquidity_index_normalized"] < b["liquidity_index_normalized"]
                elif a[LIQUIDITY_FIELD] == b[LIQUIDITY_FIELD]:
                    assert a["liquidity_index_normalized"] == b["liquidity_index_normalized"]

    @given(fund_lists(min_size=2), st.integers(1, 50), st.integers(-500, 500))
    def test_only_the_ranking_matters_not_the_scale(self, funds, scale, shift):
        # A percentile rank is unchanged by any increasing transformation of the values
        transformed = copy.deepcopy(funds)
        for fund in transformed:
            fund[LIQUIDITY_FIELD] = fund[LIQUIDITY_FIELD] * scale + shift
        normalize_liquidity(funds)
        normalize_liquidity(transformed)
        assert [f["liquidity_index_normalized"] for f in funds] == [
            f["liquidity_index_normalized"] for f in transformed
        ]

    @given(fund_lists(min_size=2))
    def test_scores_are_evenly_spaced_by_distinct_rank(self, funds):
        assume(len({f[LIQUIDITY_FIELD] for f in funds}) >= 2)
        normalize_liquidity(funds)
        distinct = sorted({f[LIQUIDITY_FIELD] for f in funds})
        for fund in funds:
            expected = distinct.index(fund[LIQUIDITY_FIELD]) / (len(distinct) - 1) * 100
            assert fund["liquidity_index_normalized"] == pytest.approx(expected)

    @given(fund_lists(min_size=1), st.data())
    def test_funds_without_data_score_zero_and_do_not_affect_the_others(self, funds, data):
        victim = data.draw(st.sampled_from(funds))
        others = copy.deepcopy([f for f in funds if f is not victim])
        victim[LIQUIDITY_FIELD] = None
        normalize_liquidity(funds)
        normalize_liquidity(others)
        assert victim["liquidity_index_normalized"] == 0.0
        by_id = {f["ID"]: f for f in funds}
        for other in others:
            assert by_id[other["ID"]]["liquidity_index_normalized"] == other["liquidity_index_normalized"]


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------


class TestGrade:
    @given(fund_lists(), weights_summing_to_100)
    def test_grade_is_the_weighted_sum_of_normalised_metrics(self, funds, weights):
        normalize_data(funds)
        fields = (*reversed(MIN_MAX_FIELDS), LIQUIDITY_FIELD)  # 1Y, 3Y, 5Y, Sharpe, liquidity
        for fund in funds:
            expected = sum(fund[f + "_normalized"] * w / 100 for f, w in zip(fields, weights))
            assert calculate_grade(fund, *weights) == pytest.approx(expected, abs=0.0051)  # rounded to 2 dp

    @given(fund_lists(), weights_summing_to_100)
    def test_grade_is_between_0_and_100(self, funds, weights):
        normalize_data(funds)
        assert all(0 <= calculate_grade(f, *weights) <= 100 for f in funds)

    @given(fund_lists(), st.lists(st.integers(0, 60), min_size=5, max_size=5))
    def test_weights_not_summing_to_100_give_no_grade(self, funds, weights):
        assume(sum(weights) != 100)
        normalize_data(funds)
        assert all(calculate_grade(f, *weights) == 0 for f in funds)

    @given(fund_lists(), weights_summing_to_100, st.data())
    def test_missing_weighted_metric_means_no_grade(self, funds, weights, data):
        fields = ("tsua_mitztaberet_letkufa", "tsua_3", "tsua_5", "sharp_ribit_hasarot_sikun", LIQUIDITY_FIELD)
        weighted = [f for f, w in zip(fields, weights) if w > 0]
        field = data.draw(st.sampled_from(weighted))
        victim = data.draw(st.sampled_from(funds))
        victim[field] = None if field == LIQUIDITY_FIELD else 0.0
        normalize_data(funds)
        assert calculate_grade(victim, *weights) == 0

    @given(fund_lists(), weights_summing_to_100)
    def test_sorting_is_by_grade_descending(self, funds, weights):
        normalize_data(funds)
        ranked = add_grade_and_sort(funds, *weights)
        grades = [f["grade"] for f in ranked]
        assert grades == sorted(grades, reverse=True)
        assert sorted(f["ID"] for f in ranked) == sorted(f["ID"] for f in funds)


# ---------------------------------------------------------------------------
# Fees and graded pools
# ---------------------------------------------------------------------------


class TestFeesAndPools:
    @given(fund_lists(), fees)
    def test_fee_is_taken_from_every_reported_return_and_gross_is_kept(self, funds, fee):
        original = copy.deepcopy(funds)
        apply_dmey_nihul(funds, fee)
        for before, after in zip(original, funds):
            for field in RETURN_FIELDS:
                assert after[f"{field}_gross"] == before[field]
                expected = before[field] - fee if before[field] != 0.0 else 0.0  # 0.0 = no data
                assert after[field] == expected

    @given(fund_lists(), fees, weights_summing_to_100)
    def test_pool_building_leaves_its_input_untouched(self, funds, fee, weights):
        snapshot = copy.deepcopy(funds)
        build_graded_pool(funds, fee, *weights)
        assert funds == snapshot

    @given(fund_lists(), fees, fees, weights_summing_to_100)
    def test_grades_do_not_depend_on_the_clients_fee(self, funds, fee_a, fee_b, weights):
        # The same fee comes off every fund — gains and losses alike — so it cannot change who is better
        pool_a = build_graded_pool(funds, fee_a, *weights)
        pool_b = build_graded_pool(funds, fee_b, *weights)
        assert [(f["ID"], f["grade"]) for f in pool_a] == [(f["ID"], f["grade"]) for f in pool_b]

    def test_a_fund_that_lost_money_does_not_escape_the_fee(self):
        from tests.conftest import make_fund

        funds = [
            make_fund("loser", tsua_1=-2.0, liquidity_index=1.0),
            make_fund("mid", tsua_1=5.0, liquidity_index=2.0),
            make_fund("top", tsua_1=10.0, liquidity_index=3.0),
        ]
        cheap = {f["ID"]: f["grade"] for f in build_graded_pool(funds, 0.1, 10, 20, 25, 35, 10)}
        pricey = {f["ID"]: f["grade"] for f in build_graded_pool(funds, 1.0, 10, 20, 25, 35, 10)}
        assert cheap == pytest.approx(pricey, abs=0.011)

    def test_a_return_that_nets_to_zero_is_still_data(self):
        from tests.conftest import make_fund

        # 0.25% less a 0.25% fee is a real 0.00% return, not the "no data" marker
        funds = [make_fund("flat", tsua_1=0.25, liquidity_index=1.0), make_fund("up", tsua_1=8.0, liquidity_index=2.0)]
        pool = {f["ID"]: f for f in build_graded_pool(funds, 0.25, 10, 20, 25, 35, 10)}
        assert pool["flat"]["tsua_mitztaberet_letkufa"] == 0.0
        assert pool["flat"]["has_grade"] is True
        assert pool["up"]["tsua_mitztaberet_letkufa_normalized"] == 100.0
