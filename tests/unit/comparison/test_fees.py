"""Unit tests for src/comparison/fees.py"""

import copy

import pytest

from src.comparison.fees import apply_dmey_nihul
from tests.conftest import make_fund


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
