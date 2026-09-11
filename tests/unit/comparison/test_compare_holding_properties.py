"""Invariants of a single holding's comparison, over randomly generated fund universes."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.comparison.service import FundUniverse, Weights, compare_holding
from tests.strategies import comparison_cases, fees

WEIGHTS = Weights(10, 20, 25, 35, 10)
_RETURN_KEYS = {"tsua_1": "tsua_mitztaberet_letkufa", "tsua_3": "tsua_3", "tsua_5": "tsua_5"}


def _run(case, weights=WEIGHTS, override=None):
    all_funds, suggestable, client_fund, mislaka = case
    universe = FundUniverse(all_funds=all_funds, suggestable=suggestable)
    return compare_holding(mislaka, client_fund, universe, weights, override)


def _peers(case, risk_level):
    all_funds, suggestable, client_fund, _ = case
    return [f for f in suggestable if f["SUG"] == client_fund["SUG"] and f["risk_level"] == risk_level]


@given(comparison_cases())
def test_rank_is_within_the_pool_and_the_pool_is_exactly_the_peers(case):
    _, suggestable, client_fund, _ = case
    client = _run(case)["client"]
    peers = _peers(case, client_fund["risk_level"])
    expected_size = len(peers) + (0 if client_fund in peers else 1)
    assert client["total_in_risk"] == expected_size
    assert 1 <= client["rank"] <= expected_size
    assert client["percentile"] == round((expected_size - client["rank"]) / expected_size * 100)


@given(comparison_cases())
def test_alternatives_are_the_best_recommendable_peers(case):
    _, _, client_fund, _ = case
    result = _run(case)
    alternatives = result["alternatives"]
    peer_ids = {f["ID"] for f in _peers(case, client_fund["risk_level"])} - {client_fund["ID"]}
    assert len(alternatives) == min(3, len(peer_ids))
    assert {a["id"] for a in alternatives} <= peer_ids
    grades = [a["grade"] for a in alternatives]
    assert grades == sorted(grades, reverse=True)
    assert len({a["id"] for a in alternatives}) == len(alternatives)


@given(comparison_cases())
def test_alternative_ranks_are_positions_in_the_pool(case):
    result = _run(case)
    client_rank = result["client"]["rank"]
    ranks = [a["rank"] for a in result["alternatives"]]
    expected = [r for r in range(1, len(ranks) + 2) if r != client_rank][: len(ranks)]
    assert ranks == expected


@given(comparison_cases())
def test_gross_returns_add_back_exactly_the_clients_fee(case):
    fee = case[3]["SHEUR-DMEI-NIHUL-TZVIRA"]
    by_id = {f["ID"]: f for f in case[0]}
    result = _run(case)
    for option in [*result["alternatives"], *([result["golden"]] if result["golden"] else [])]:
        raw = by_id[option["id"]]
        for key, field in _RETURN_KEYS.items():
            assert option["gross"][key] == round(raw[field], 2)
            expected_net = raw[field] - fee if raw[field] != 0.0 else 0.0
            assert option[key] == round(expected_net, 2)


@given(comparison_cases())
def test_client_return_is_net_of_the_fee(case):
    _, _, client_fund, mislaka = case
    fee = mislaka["SHEUR-DMEI-NIHUL-TZVIRA"]
    client = _run(case)["client"]
    for key, field in _RETURN_KEYS.items():
        raw = client_fund[field]
        assert client[key] == round(raw - fee if raw != 0.0 else 0.0, 2)


@given(comparison_cases())
def test_projection_fields_are_consistent(case):
    money = case[3]["TOTAL-CHISACHON-MTZBR"]
    result = _run(case)
    for option in [*result["alternatives"], *([result["golden"]] if result["golden"] else [])]:
        for figures in (option, option["gross"]):
            for suffix in ("", "_3", "_5"):
                potential = figures[f"potential_amount{suffix}"]
                if potential is None:
                    assert figures[f"diff{suffix}"] is None and figures[f"diff_percent{suffix}"] is None
                    continue
                assert figures[f"diff{suffix}"] == pytest.approx(potential - money, abs=0.011)
                assert figures[f"diff_percent{suffix}"] == pytest.approx((potential - money) / money * 100, abs=0.051)


@given(comparison_cases())
def test_no_fee_in_the_new_fund_never_projects_less(case):
    result = _run(case)
    for option in result["alternatives"]:
        for suffix in ("", "_3", "_5"):
            assert option["gross"][f"potential_amount{suffix}"] >= option[f"potential_amount{suffix}"]


@given(comparison_cases(), fees)
def test_the_clients_fee_does_not_change_grades_or_ranking(case, other_fee):
    all_funds, suggestable, client_fund, mislaka = case
    first = _run(case)
    second = _run((all_funds, suggestable, client_fund, {**mislaka, "SHEUR-DMEI-NIHUL-TZVIRA": other_fee}))
    assert first["client"]["grade"] == second["client"]["grade"]
    assert first["client"]["rank"] == second["client"]["rank"]
    assert [(a["id"], a["grade"]) for a in first["alternatives"]] == [
        (a["id"], a["grade"]) for a in second["alternatives"]
    ]


@given(comparison_cases())
def test_golden_is_a_better_high_risk_fund_for_lower_risk_clients_only(case):
    _, _, client_fund, _ = case
    result = _run(case)
    golden = result["golden"]
    if client_fund["risk_level"] == "high":
        assert golden == {}
        return
    high_peers = {f["ID"] for f in _peers(case, "high")}
    if not golden:
        return
    assert golden["id"] in high_peers
    best_same_risk = result["alternatives"][0]["potential_amount"] if result["alternatives"] else None
    assert golden["potential_amount"] is not None
    if best_same_risk is not None:
        assert golden["potential_amount"] > best_same_risk


@given(comparison_cases(), st.sampled_from(["low", "medium", "high"]))
def test_override_compares_against_that_risk_level_without_golden(case, level):
    _, _, client_fund, _ = case
    result = _run(case, override=level)
    peer_ids = {f["ID"] for f in _peers(case, level)} - {client_fund["ID"]}
    assert {a["id"] for a in result["alternatives"]} <= peer_ids
    assert result["golden"] == {}
    assert result["client"]["risk_level"] == client_fund["risk_level"]


@given(comparison_cases())
def test_money_and_identity_come_from_the_holding(case):
    _, _, client_fund, mislaka = case
    client = _run(case)["client"]
    assert client["id"] == client_fund["ID"]
    assert client["amount"] == mislaka["TOTAL-CHISACHON-MTZBR"]
    assert client["dmei_nihul"] == mislaka["SHEUR-DMEI-NIHUL-TZVIRA"]
    assert client["hevra"] == client_fund["hevra"]
    assert client["equity_exposure"] == client_fund["equity_exposure"]
    assert client["israel_equity_share"] == client_fund["israel_equity_share"]
