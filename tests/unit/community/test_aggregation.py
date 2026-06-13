"""Unit tests for src/community/aggregation.py"""

import pytest

from src.community.aggregation import (
    apply_percentages,
    build_profile_payload,
    dominant_risk,
    shorten_join_date,
    to_funds_json,
    to_leaderboard_row,
    to_profile_dict,
    weighted_equity_exposure,
    weighted_score,
    weighted_tsua,
)


def _sample_funds(risk_levels=("medium", "high"), amounts=(50000, 80000)):
    return [
        {
            "name": f"Fund {i}",
            "id": str(1000 + i),
            "risk_level": risk_levels[i],
            "tsua_1": 10.0 + i,
            "grade": 70.0 + i * 5,
            "amount": amounts[i],
            "equity_exposure": 50.0 + i * 10,
        }
        for i in range(len(risk_levels))
    ]


class TestApplyPercentages:
    def test_adds_pct_of_total_field(self):
        result = apply_percentages(_sample_funds())
        assert all("pct_of_total" in f for f in result)

    def test_percentages_sum_to_100(self):
        result = apply_percentages(_sample_funds())
        assert abs(sum(f["pct_of_total"] for f in result) - 100.0) < 0.1

    def test_zero_total_amount_does_not_crash(self):
        result = apply_percentages(_sample_funds(amounts=(0, 0)))
        assert all(f["pct_of_total"] == 0.0 for f in result)

    def test_empty_list_returns_empty(self):
        assert apply_percentages([]) == []


class TestWeightedTsua:
    def test_calculates_weighted_average(self):
        funds = _sample_funds()
        total = sum(f["amount"] for f in funds)
        expected = sum(f["tsua_1"] * f["amount"] / total for f in funds)
        result = weighted_tsua(apply_percentages(funds))
        assert abs(result - expected) < 1e-2

    def test_empty_list_returns_zero(self):
        assert weighted_tsua([]) == 0


class TestWeightedScore:
    def test_ignores_non_positive_grades(self):
        funds = apply_percentages([
            {**_sample_funds()[0], "grade": 0},
            _sample_funds()[1],
        ])
        result = weighted_score(funds)
        assert result == pytest.approx(funds[1]["grade"] * funds[1]["pct_of_total"] / 100)

    def test_empty_list_returns_zero(self):
        assert weighted_score([]) == 0


class TestWeightedEquityExposure:
    def test_computed_from_exposure_funds(self):
        funds = apply_percentages(_sample_funds())
        result = weighted_equity_exposure(funds)
        assert isinstance(result, float)

    def test_none_when_no_exposure_data(self):
        funds = apply_percentages([{**f, "equity_exposure": None} for f in _sample_funds()])
        assert weighted_equity_exposure(funds) is None

    def test_none_for_empty_list(self):
        assert weighted_equity_exposure([]) is None


class TestDominantRisk:
    def test_returns_highest_weighted_risk(self):
        funds = apply_percentages([
            {"risk_level": "medium", "amount": 40000},
            {"risk_level": "medium", "amount": 40000},
            {"risk_level": "high", "amount": 20000},
        ])
        assert dominant_risk(funds) == "medium"

    def test_empty_list_defaults_to_high(self):
        assert dominant_risk([]) == "high"

    def test_missing_risk_level_defaults_to_high(self):
        funds = apply_percentages([{"amount": 100}])
        assert dominant_risk(funds) == "high"


class TestToFundsJson:
    def test_extracts_name_id_pct(self):
        funds = apply_percentages(_sample_funds())
        result = to_funds_json(funds)
        for entry in result:
            assert set(entry.keys()) == {"name", "id", "pct"}


class TestBuildProfilePayload:
    def test_rounds_values(self):
        payload = build_profile_payload("נשר 10", 12.345, 88.999, "high", 80.06, [], "01/01/2025")
        assert payload["weighted_tsua"] == 12.35
        assert payload["weighted_score"] == 89.0
        assert payload["weighted_equity_exposure"] == 80.1

    def test_none_equity_exposure_stays_none(self):
        payload = build_profile_payload("X", 1.0, 1.0, "low", None, [], "01/01/2025")
        assert payload["weighted_equity_exposure"] is None


class TestShortenJoinDate:
    def test_full_date_to_month_year(self):
        assert shorten_join_date("01/01/2025") == "01/2025"

    def test_already_short_returns_unchanged(self):
        assert shorten_join_date("01/2025") == "01/2025"

    def test_empty_string_returns_unchanged(self):
        assert shorten_join_date("") == ""


class TestToLeaderboardRow:
    def test_shapes_row_with_num_funds(self):
        row = {
            "fake_name": "נשר 10",
            "weighted_tsua": 12.5,
            "weighted_score": 88.0,
            "dominant_risk": "high",
            "weighted_equity_exposure": 80.0,
            "funds": '[{"name":"F","id":"1","pct":100.0}]',
            "joined": "01/01/2025",
        }
        result = to_leaderboard_row(row)
        assert result["num_funds"] == 1
        assert result["joined"] == "01/2025"

    def test_handles_already_parsed_funds_list(self):
        row = {
            "fake_name": "X", "weighted_tsua": 1.0, "weighted_score": 1.0,
            "dominant_risk": "low", "weighted_equity_exposure": None,
            "funds": [{"name": "A", "id": "1", "pct": 100.0}],
            "joined": "01/01/2025",
        }
        result = to_leaderboard_row(row)
        assert result["num_funds"] == 1

    def test_handles_none_funds(self):
        row = {
            "fake_name": "X", "weighted_tsua": 1.0, "weighted_score": 1.0,
            "dominant_risk": "low", "weighted_equity_exposure": None,
            "funds": None, "joined": "",
        }
        result = to_leaderboard_row(row)
        assert result["num_funds"] == 0


class TestToProfileDict:
    def test_parses_funds_json_string(self):
        row = {
            "fake_name": "נשר 42", "weighted_tsua": 11.0, "weighted_score": 80.0,
            "dominant_risk": "medium", "weighted_equity_exposure": 55.0,
            "joined": "10/04/2025", "funds": '[{"name":"F","id":"1","pct":100.0}]',
        }
        result = to_profile_dict(row)
        assert result["fake_name"] == "נשר 42"
        assert isinstance(result["funds"], list)
        assert result["funds"][0]["name"] == "F"

    def test_handles_none_funds(self):
        row = {
            "fake_name": "X", "weighted_tsua": 0.0, "weighted_score": 0.0,
            "dominant_risk": "low", "weighted_equity_exposure": None,
            "joined": "01/01/2025", "funds": None,
        }
        result = to_profile_dict(row)
        assert result["funds"] == []
