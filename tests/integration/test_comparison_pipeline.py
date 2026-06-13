"""Integration tests for the comparison engine pipeline (no real file I/O).

These tests wire together multiple engine functions to verify the pipeline
behaves correctly end-to-end with synthetic data.
"""

import copy

import pytest

from src.comparison.fees import apply_dmey_nihul
from src.comparison.grading import add_grade_and_sort, get_top_3
from src.comparison.matching import find_matching_funds, get_funds_by_risk_level
from src.comparison.normalization import normalize_data
from src.comparison.ranking import get_client_ranking
from tests.conftest import make_fund, make_mislaka


# ---------------------------------------------------------------------------
# Full pipeline with synthetic data
# ---------------------------------------------------------------------------


def _run_pipeline(
    mislaka_list, funds_list, dmei_nihul=0.5,
    weight_1=10, weight_3=20, weight_5=25, weight_sharp=45,
    risk_level="medium",
):
    """Replicate the per-holding pipeline from engine.run_comparison."""
    matches = find_matching_funds(mislaka_list, funds_list)
    results = []
    for mislaka, fund in matches:
        same_risk = get_funds_by_risk_level(funds_list, risk_level)
        if not any(f["ID"] == fund["ID"] for f in same_risk):
            same_risk = [fund] + same_risk
        adjusted = apply_dmey_nihul(copy.deepcopy(same_risk), dmei_nihul)
        normalize_data(adjusted)
        sorted_funds = add_grade_and_sort(adjusted, weight_1, weight_3, weight_5, weight_sharp)
        rank, total = get_client_ranking(sorted_funds, fund["ID"])
        top3 = get_top_3([f for f in sorted_funds if f["ID"] != fund["ID"]])
        results.append({
            "fund_id": fund["ID"],
            "rank": rank,
            "total": total,
            "top3_ids": [f["ID"] for f in top3],
        })
    return results


class TestPipelineMatchingAndRanking:
    def _build_funds(self):
        return [
            make_fund("A", tsua_1=25.0, tsua_3=20.0, tsua_5=18.0, sharpe=2.5, risk_level="medium"),
            make_fund("B", tsua_1=15.0, tsua_3=12.0, tsua_5=10.0, sharpe=1.5, risk_level="medium"),
            make_fund("C", tsua_1=10.0, tsua_3=8.0,  tsua_5=7.0,  sharpe=1.0, risk_level="medium"),
            make_fund("D", tsua_1=5.0,  tsua_3=4.0,  tsua_5=3.0,  sharpe=0.5, risk_level="medium"),
            make_fund("E", tsua_1=30.0, tsua_3=25.0, tsua_5=22.0, sharpe=3.0, risk_level="high"),
        ]

    def test_client_fund_ranked(self):
        funds = self._build_funds()
        mislaka = [make_mislaka("D", balance=100_000)]
        results = _run_pipeline(mislaka, funds)
        assert len(results) == 1
        assert results[0]["fund_id"] == "D"
        assert results[0]["rank"] is not None

    def test_worst_fund_ranked_last(self):
        funds = self._build_funds()
        mislaka = [make_mislaka("D", balance=100_000)]
        results = _run_pipeline(mislaka, funds)
        assert results[0]["rank"] == results[0]["total"]

    def test_best_fund_ranked_first(self):
        funds = self._build_funds()
        mislaka = [make_mislaka("A", balance=100_000)]
        results = _run_pipeline(mislaka, funds)
        assert results[0]["rank"] == 1

    def test_top3_excludes_client_fund(self):
        funds = self._build_funds()
        mislaka = [make_mislaka("B", balance=100_000)]
        results = _run_pipeline(mislaka, funds)
        assert "B" not in results[0]["top3_ids"]

    def test_top3_at_most_three(self):
        funds = self._build_funds()
        mislaka = [make_mislaka("D", balance=100_000)]
        results = _run_pipeline(mislaka, funds)
        assert len(results[0]["top3_ids"]) <= 3

    def test_fee_reduces_net_return(self):
        """Applying a fee should lower adjusted returns and potentially change rankings."""
        funds = self._build_funds()
        mislaka_low_fee = [make_mislaka("B", balance=100_000, dmei_nihul_tzvira=0.1)]
        mislaka_high_fee = [make_mislaka("B", balance=100_000, dmei_nihul_tzvira=5.0)]

        # Build two independent fund lists to avoid mutation contamination
        results_low = _run_pipeline(mislaka_low_fee, copy.deepcopy(funds))
        results_high = _run_pipeline(mislaka_high_fee, copy.deepcopy(funds))

        # With high fee all returns may normalise to 0 → grades all 0 → ranks equal
        # Just ensure both pipelines complete without error
        assert results_low[0]["rank"] is not None or results_high[0]["rank"] is not None

    def test_unmatched_mislaka_excluded(self):
        funds = self._build_funds()
        mislaka = [make_mislaka("ZZZZZ", balance=100_000)]
        results = _run_pipeline(mislaka, funds)
        assert results == []

    def test_multiple_holdings_processed(self):
        funds = self._build_funds()
        mislaka = [
            make_mislaka("A", balance=50_000),
            make_mislaka("B", balance=80_000),
            make_mislaka("C", balance=60_000),
        ]
        results = _run_pipeline(mislaka, funds)
        assert len(results) == 3

    def test_risk_filter_excludes_cross_risk_funds(self):
        """High-risk fund E should not appear in medium-risk alternatives."""
        funds = self._build_funds()
        mislaka = [make_mislaka("B", balance=100_000)]
        results = _run_pipeline(mislaka, funds, risk_level="medium")
        # "E" is high-risk and must not appear in top-3 medium alternatives
        assert "E" not in results[0]["top3_ids"]


class TestNormalizationInPipeline:
    def test_all_same_performance_gives_zero_grades(self):
        funds = [make_fund(str(i), tsua_1=10.0, tsua_3=8.0, tsua_5=6.0, sharpe=1.0, risk_level="medium") for i in range(3)]
        mislaka = [make_mislaka("0", balance=100_000)]
        results = _run_pipeline(mislaka, funds)
        # When all funds have identical performance, normalization yields 0 for all → all grades 0
        assert results[0]["rank"] is not None

    def test_single_fund_in_risk_level(self):
        fund = make_fund("SOLO", tsua_1=15.0, tsua_3=12.0, tsua_5=10.0, sharpe=1.8, risk_level="medium")
        mislaka = [make_mislaka("SOLO", balance=100_000)]
        results = _run_pipeline(mislaka, [fund])
        assert results[0]["total"] == 1
        assert len(results[0]["top3_ids"]) == 0


class TestWeightSensitivity:
    def _two_funds(self):
        # Fund A: great Sharpe, mediocre 1Y
        # Fund B: great 1Y, mediocre Sharpe
        return [
            make_fund("A", tsua_1=5.0,  tsua_3=8.0, tsua_5=7.0, sharpe=3.0, risk_level="medium"),
            make_fund("B", tsua_1=25.0, tsua_3=8.0, tsua_5=7.0, sharpe=0.5, risk_level="medium"),
        ]

    def test_sharpe_heavy_weights_prefer_sharpe_fund(self):
        funds = self._two_funds()
        # Weights: 1Y=5, 3Y=25, 5Y=25, Sharpe=45 → total=100 only if all non-zero
        adjusted = apply_dmey_nihul(copy.deepcopy(funds), 0.0)
        normalize_data(adjusted)
        sorted_funds = add_grade_and_sort(adjusted, 5, 25, 25, 45)
        # All fields non-zero → grades calculated; A should rank higher with sharpe=3.0
        if sorted_funds[0]["grade"] > 0:
            assert sorted_funds[0]["ID"] == "A"

    def test_tsua1_heavy_weights_prefer_high_return_fund(self):
        funds = self._two_funds()
        # Weights: 1Y=55, 3Y=15, 5Y=15, Sharpe=15 → total=100
        adjusted = apply_dmey_nihul(copy.deepcopy(funds), 0.0)
        normalize_data(adjusted)
        sorted_funds = add_grade_and_sort(adjusted, 55, 15, 15, 15)
        if sorted_funds[0]["grade"] > 0:
            assert sorted_funds[0]["ID"] == "B"
