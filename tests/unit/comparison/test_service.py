"""Unit tests for src/comparison/service.py (synthetic fund universes, no real data files)."""

import dataclasses
from unittest.mock import patch

import pytest

from src.comparison import service
from src.comparison.service import (
    FundUniverse,
    Weights,
    compare_holding,
    load_fund_universe,
    run_bulk_comparison,
    run_comparison,
)
from tests.conftest import (
    MINIMAL_FUNDS_XML,
    MINIMAL_MISLAKA_XML,
    make_fund,
    make_mislaka,
)

WEIGHTS = Weights(10, 20, 25, 35, 10)


def _funds():
    """Medium-risk A > B > C > D on every metric, plus one high-risk fund H."""
    return [
        make_fund("A", fund_name="Fund A", hevra="Alpha", tsua_1=25.0, tsua_3=20.0, tsua_5=18.0, sharpe=2.5,
                  liquidity_index=30.0, equity_exposure=60.0, foreign_exposure=15.0),
        make_fund("B", fund_name="Fund B", hevra="Beta", tsua_1=15.0, tsua_3=12.0, tsua_5=10.0, sharpe=1.5,
                  liquidity_index=5.0, equity_exposure=50.0, foreign_exposure=45.0),
        make_fund("C", fund_name="Fund C", hevra="Gamma", tsua_1=10.0, tsua_3=8.0, tsua_5=7.0, sharpe=1.0,
                  liquidity_index=-2.0),
        make_fund("D", fund_name="Fund D", hevra="Delta", tsua_1=5.0, tsua_3=4.0, tsua_5=3.0, sharpe=0.5,
                  liquidity_index=-20.0),
        make_fund("H", fund_name="Fund H", hevra="Eta", tsua_1=40.0, tsua_3=30.0, tsua_5=25.0, sharpe=3.0,
                  liquidity_index=10.0, risk_level="high"),
    ]


def _universe(funds=None, suggestable=None):
    funds = funds if funds is not None else _funds()
    return FundUniverse(all_funds=funds, suggestable=suggestable if suggestable is not None else funds)


def _compare(fund_id, universe=None, balance=100_000.0, fee=0.5, weights=WEIGHTS, override=None):
    universe = universe or _universe()
    fund = next(f for f in universe.all_funds if f["ID"] == fund_id)
    mislaka = make_mislaka(fund_id, balance=balance, dmei_nihul_tzvira=fee)
    return compare_holding(mislaka, fund, universe, weights, override)


# ---------------------------------------------------------------------------
# The full payload, computed by hand
# ---------------------------------------------------------------------------


class TestGoldenMaster:
    """Client in D (worst medium fund), fee 0.5%, ₪100,000; every figure worked out by hand.

    Net returns (fee off everyone): A 24.5/19.5/17.5, B 14.5/11.5/9.5, C 9.5/7.5/6.5,
    D 4.5/3.5/2.5. Normalised: 1Y A100 B50 C25 D0; 3Y A100 B50 C25 D0; 5Y A100 B46.67
    C26.67 D0; Sharpe A100 B50 C25 D0; liquidity (distinct rank) A100 B66.67 C33.33 D0.
    Grades at 10/20/25/35/10: A 100, B 50.83, C 26.25, D 0.
    Projection = 100,000 × (1+option%)^years / (1+4.5% | 3.5% | 2.5%)^years.
    """

    @pytest.fixture(scope="class")
    def result(self):
        return _compare("D")

    def test_client(self, result):
        assert result["client"] == {
            "name": "Fund D",
            "id": "D",
            "client_id": "123456789",
            "client_name": "",
            "grade": 0.0,
            "has_grade": True,
            "default_grade": 0.0,
            "rank": 4,
            "total_in_risk": 4,
            "risk_level": "medium",
            "amount": 100_000.0,
            "dmei_nihul": 0.5,
            "tsua_1": 4.5,
            "tsua_3": 3.5,
            "tsua_5": 2.5,
            "hevra": "Delta",
            "seniority_date": "01/01/2020",
            "percentile": 0,
            "equity_exposure": 50.0,
            "foreign_exposure": None,
            "israel_equity_exposure": None,
            "israel_equity_share": None,
            "liquidity_index": -20.0,
            "liquidity_score": 0.0,
        }

    def test_best_alternative(self, result):
        assert result["alternatives"][0] == {
            "name": "Fund A",
            "id": "A",
            "grade": 100.0,
            "has_grade": True,
            "rank": 1,
            "hevra": "Alpha",
            "tsua_1": 24.5, "tsua_3": 19.5, "tsua_5": 17.5,
            "potential_amount": 119138.76, "diff": 19138.76, "diff_percent": 19.1,
            "potential_amount_3": 153915.61, "diff_3": 53915.61, "diff_percent_3": 53.9,
            "potential_amount_5": 197956.61, "diff_5": 97956.61, "diff_percent_5": 98.0,
            "gross": {
                "tsua_1": 25.0, "tsua_3": 20.0, "tsua_5": 18.0,
                "potential_amount": 119617.22, "diff": 19617.22, "diff_percent": 19.6,
                "potential_amount_3": 155855.7, "diff_3": 55855.7, "diff_percent_3": 55.9,
                "potential_amount_5": 202204.45, "diff_5": 102204.45, "diff_percent_5": 102.2,
            },
            "equity_exposure": 60.0,
            "foreign_exposure": 15.0,
            "israel_equity_exposure": 45.0,
            "israel_equity_share": 75.0,
            "liquidity_index": 30.0,
            "liquidity_score": 100.0,
        }

    def test_other_alternatives(self, result):
        second, third = result["alternatives"][1:]
        assert (second["id"], second["grade"], second["rank"]) == ("B", 50.83, 2)
        assert (third["id"], third["grade"], third["rank"]) == ("C", 26.25, 3)
        assert (second["potential_amount_3"], second["gross"]["diff_percent_5"]) == (125026.93, 42.3)
        assert (third["potential_amount_5"], third["gross"]["diff"]) == (121095.7, 5263.16)
        assert (second["israel_equity_share"], second["liquidity_score"]) == (10.0, 66.7)
        assert third["liquidity_score"] == 33.3

    def test_golden_option(self, result):
        golden = result["golden"]
        # H is the only high-risk fund: min == max everywhere, liquidity rank neutral 50 -> 5.0
        assert (golden["id"], golden["rank"], golden["grade"]) == ("H", 1, 5.0)
        assert (golden["potential_amount"], golden["diff_percent"]) == (133492.82, 33.5)
        assert (golden["gross"]["potential_amount_5"], golden["gross"]["diff_5"]) == (269730.92, 169730.92)

    def test_default_grade_uses_the_community_weights(self):
        # 10/20/25/45 with no liquidity weight is not the default any more
        result = _compare("B", weights=Weights(10, 20, 25, 45, 0))
        assert result["client"]["grade"] != result["client"]["default_grade"]
        assert result["client"]["default_grade"] == 50.83


# ---------------------------------------------------------------------------
# Peer pool and ranking
# ---------------------------------------------------------------------------


class TestPeerPool:
    def test_client_fund_counted_once(self):
        assert _compare("D")["client"]["total_in_risk"] == 4

    def test_non_recommendable_client_fund_is_ranked_but_not_suggested(self):
        funds = _funds()
        universe = _universe(funds, suggestable=[f for f in funds if f["ID"] != "B"])
        result = _compare("B", universe)
        assert result["client"]["total_in_risk"] == 4
        assert [a["id"] for a in result["alternatives"]] == ["A", "C", "D"]

    def test_other_non_recommendable_funds_stay_out(self):
        funds = _funds()
        universe = _universe(funds, suggestable=[f for f in funds if f["ID"] != "A"])
        result = _compare("D", universe)
        assert result["client"]["total_in_risk"] == 3
        assert "A" not in [a["id"] for a in result["alternatives"]]

    def test_alternative_ranks_count_the_client(self):
        # Client is #2, so the alternatives are #1, #3, #4
        result = _compare("B")
        assert [(a["id"], a["rank"]) for a in result["alternatives"]] == [("A", 1), ("C", 3), ("D", 4)]
        assert (result["client"]["rank"], result["client"]["percentile"]) == (2, 50)

    def test_other_fund_types_are_not_peers(self):
        funds = _funds()
        funds[0]["SUG"] = "קרנות השתלמות"
        result = _compare("D", _universe(funds))
        assert result["client"]["total_in_risk"] == 3
        assert "A" not in [a["id"] for a in result["alternatives"]]

    def test_override_compares_against_another_risk_level(self):
        result = _compare("D", override="high")
        assert result["client"]["risk_level"] == "medium"
        assert result["client"]["total_in_risk"] == 2
        assert [a["id"] for a in result["alternatives"]] == ["H"]
        assert result["golden"] == {}

    def test_balance_of_exactly_one_shekel_counts(self):
        assert _compare("D", balance=1.0) is not None
        assert _compare("D", balance=0.99) is None


class TestPayloadDetails:
    def test_client_name_comes_from_the_holding(self):
        universe = _universe()
        mislaka = {**make_mislaka("D"), "SHEM-LAKOACH": "דנה כהן"}
        fund = next(f for f in universe.all_funds if f["ID"] == "D")
        result = compare_holding(mislaka, fund, universe, WEIGHTS)
        assert result["client"]["client_name"] == "דנה כהן"

    def test_returns_and_liquidity_are_rounded(self):
        funds = _funds()
        funds[0]["tsua_mitztaberet_letkufa"] = 10.1          # 10.1 - 0.3 is 9.799999999999999
        funds[0]["liquidity_index"] = 4657.31 / 24824.09 * 100  # 18.76125…
        best = _compare("D", _universe(funds), fee=0.3)["alternatives"][0]
        assert best["id"] == "A"
        assert (best["tsua_1"], best["gross"]["tsua_1"], best["liquidity_index"]) == (9.8, 10.1, 18.76)

    def test_four_weights_still_work(self):
        assert Weights(10, 20, 25, 45).liquidity == 0

    def test_universe_is_immutable(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            _universe().all_funds = []


class TestGrades:
    def test_weakest_on_every_metric_is_scored_zero_not_missing(self):
        client = _compare("D")["client"]
        assert (client["grade"], client["has_grade"]) == (0.0, True)

    def test_missing_data_has_no_grade(self):
        funds = _funds()
        funds[3]["tsua_5"] = 0.0  # D has no 5-year history
        client = _compare("D", _universe(funds))["client"]
        assert (client["grade"], client["has_grade"]) == (0, False)

    def test_fund_lowest_on_one_metric_gets_a_real_grade(self):
        funds = _funds()
        funds[2]["tsua_mitztaberet_letkufa"] = 1.0  # C: worst 1Y, otherwise middling
        assert _compare("C", _universe(funds))["client"]["grade"] > 0


# ---------------------------------------------------------------------------
# Fees and projections
# ---------------------------------------------------------------------------


class TestFeesAndProjections:
    def test_gross_is_net_plus_the_clients_fee(self):
        for alt in _compare("D", fee=0.75)["alternatives"]:
            for key in ("tsua_1", "tsua_3", "tsua_5"):
                assert alt["gross"][key] == pytest.approx(alt[key] + 0.75)

    def test_fee_does_not_change_grades_or_ranks(self):
        cheap, pricey = _compare("C", fee=0.1), _compare("C", fee=1.2)
        assert cheap["client"]["grade"] == pytest.approx(pricey["client"]["grade"], abs=0.011)
        assert [a["id"] for a in cheap["alternatives"]] == [a["id"] for a in pricey["alternatives"]]

    def test_projection_is_none_without_data_on_either_side(self):
        funds = _funds()
        funds[3]["tsua_3"] = 0.0  # client D has no 3-year history
        result = _compare("D", _universe(funds), weights=Weights(20, 0, 45, 35, 0))
        best = result["alternatives"][0]
        assert (best["potential_amount_3"], best["diff_3"], best["diff_percent_3"]) == (None, None, None)
        assert best["gross"]["potential_amount_3"] is None
        assert best["potential_amount"] == 119138.76

    def test_option_without_data_has_no_projection(self):
        funds = _funds()
        funds[0]["tsua_5"] = 0.0  # A has no 5-year history
        best = _compare("D", _universe(funds), weights=Weights(20, 45, 0, 35, 0))["alternatives"][0]
        assert best["id"] == "A"
        assert best["potential_amount_5"] is None
        assert best["potential_amount_3"] == 153915.61


# ---------------------------------------------------------------------------
# Golden (higher-risk) option
# ---------------------------------------------------------------------------


class TestGoldenOption:
    def _with_high_fund(self, tsua_1):
        funds = [f for f in _funds() if f["ID"] != "H"]
        funds.append(make_fund("H", risk_level="high", tsua_1=tsua_1, tsua_3=30.0, tsua_5=25.0,
                               sharpe=3.0, liquidity_index=10.0))
        return _universe(funds)

    def test_offered_when_it_beats_the_best_same_risk_fund(self):
        assert _compare("D")["golden"]["id"] == "H"

    def test_not_offered_when_the_best_same_risk_fund_is_better(self):
        assert _compare("D", self._with_high_fund(tsua_1=20.0))["golden"] == {}

    def test_not_offered_on_a_tie(self):
        # Same 1-year return as A, the best same-risk fund
        assert _compare("D", self._with_high_fund(tsua_1=25.0))["golden"] == {}

    def test_not_offered_to_a_high_risk_client(self):
        funds = _funds()
        funds.append(make_fund("H2", risk_level="high", tsua_1=50.0, tsua_3=40.0, tsua_5=30.0, sharpe=4.0,
                               liquidity_index=50.0))
        assert _compare("H", _universe(funds))["golden"] == {}

    def test_offered_when_the_client_has_no_same_risk_peers(self):
        funds = [make_fund("L", risk_level="low", liquidity_index=1.0), *(_funds()[-1:])]
        assert _compare("L", _universe(funds))["golden"]["id"] == "H"

    def test_benchmark_is_the_best_other_fund_not_the_clients_own(self):
        # Client A is #1; B beats H over one year, H beats staying in A -> no golden
        funds = [f for f in _funds() if f["ID"] != "H"]
        funds[1]["tsua_mitztaberet_letkufa"] = 40.0
        funds.append(make_fund("H", risk_level="high", tsua_1=30.0, liquidity_index=1.0))
        assert _compare("A", _universe(funds))["golden"] == {}

    def test_not_offered_without_one_year_data(self):
        assert _compare("D", self._with_high_fund(tsua_1=0.0), weights=Weights(0, 30, 35, 35, 0))["golden"] == {}


# ---------------------------------------------------------------------------
# Loading the fund universe
# ---------------------------------------------------------------------------


_RISKS_XML = """\
<ROWSET>
  <Row><SHM_SUG_NECHES>, חשיפה למניות</SHM_SUG_NECHES><ID_KUPA>1001</ID_KUPA><ACHUZ_SUG_NECHES>50.0</ACHUZ_SUG_NECHES></Row>
  <Row><SHM_SUG_NECHES>חשיפה לחו"ל</SHM_SUG_NECHES><ID_KUPA>1001</ID_KUPA><ACHUZ_SUG_NECHES>10.0</ACHUZ_SUG_NECHES></Row>
  <Row><SHM_SUG_NECHES>, חשיפה למניות</SHM_SUG_NECHES><ID_KUPA>1002</ID_KUPA><ACHUZ_SUG_NECHES>50.0</ACHUZ_SUG_NECHES></Row>
  <Row><SHM_SUG_NECHES>חשיפה לחו"ל</SHM_SUG_NECHES><ID_KUPA>1002</ID_KUPA><ACHUZ_SUG_NECHES>45.0</ACHUZ_SUG_NECHES></Row>
  <Row><SHM_SUG_NECHES>, חשיפה למניות</SHM_SUG_NECHES><ID_KUPA>1003</ID_KUPA><ACHUZ_SUG_NECHES>90.0</ACHUZ_SUG_NECHES></Row>
</ROWSET>
"""


class TestLoadFundUniverse:
    @pytest.fixture(autouse=True)
    def _data_files(self, tmp_path, monkeypatch):
        (tmp_path / "funds.xml").write_text(MINIMAL_FUNDS_XML, encoding="utf-8")
        (tmp_path / "risks.xml").write_text(_RISKS_XML, encoding="utf-8")
        monkeypatch.setattr(service, "GEMEL_NET_PATH", tmp_path / "funds.xml")
        monkeypatch.setattr(service, "RISKS_MAP_PATH", tmp_path / "risks.xml")

    def test_all_funds_include_special_populations_but_suggestions_do_not(self):
        universe = load_fund_universe(25, 75, [])
        assert [f["ID"] for f in universe.all_funds] == ["1001", "1002", "1003", "9999"]
        assert [f["ID"] for f in universe.suggestable] == ["1001", "1002", "1003"]

    def test_excluded_companies_are_not_suggested(self):
        universe = load_fund_universe(25, 75, ["Hevra B"])
        assert [f["ID"] for f in universe.suggestable] == ["1001", "1003"]
        assert len(universe.all_funds) == 4

    def test_israel_share_range_limits_suggestions(self):
        # 1001: 40/50 of the equity is Israeli (80%); 1002: 5/50 (10%); 1003: unknown foreign exposure
        universe = load_fund_universe(25, 75, [], israel_share_min=60, israel_share_max=100)
        assert [f["ID"] for f in universe.suggestable] == ["1001"]

    def test_thresholds_set_risk_levels(self):
        universe = load_fund_universe(60, 80, [])
        assert {f["ID"]: f["risk_level"] for f in universe.all_funds} == {
            "1001": "low", "1002": "low", "1003": "high", "9999": "invalid",
        }


# ---------------------------------------------------------------------------
# run_comparison
# ---------------------------------------------------------------------------


class TestRunComparison:
    def test_old_clients_without_the_new_fields_keep_working(self):
        # Four weights summing to 100 and no liquidity/Israel arguments: liquidity weight
        # defaults to 0 and there is no geography filter.
        funds = [make_fund(str(i), tsua_1=float(i), tsua_3=float(i), tsua_5=float(i), sharpe=i / 10)
                 for i in (1001, 2, 3)]
        with patch.object(service, "load_fund_universe", return_value=_universe(funds)) as loader:
            result = run_comparison([MINIMAL_MISLAKA_XML], 10, 20, 25, 45, 25, 75, [])
        loader.assert_called_once_with(25, 75, [], 0.0, 100.0)
        assert result["funds"][0]["client"]["grade"] == 100.0

    def test_returns_holdings_and_portfolio(self):
        funds = [make_fund("1001", liquidity_index=1.0), make_fund("2", tsua_1=30.0, liquidity_index=2.0)]
        with patch.object(service, "load_fund_universe", return_value=_universe(funds)):
            result = run_comparison([MINIMAL_MISLAKA_XML], 10, 20, 25, 35, 25, 75, [], weight_liquidity=10)
        assert [h["client"]["id"] for h in result["funds"]] == ["1001"]
        assert result["portfolio"]["total_amount"] == 200_000.0
        assert result["portfolio"]["holdings_count"] == 1

    def test_weights_are_immutable(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            WEIGHTS.sharpe = 50


# ---------------------------------------------------------------------------
# run_bulk_comparison
# ---------------------------------------------------------------------------


def _mislaka_xml(client_id, fund_code="XX000004", balance="100000.0", name=None):
    xml = MINIMAL_MISLAKA_XML.replace("XX001001", fund_code).replace("200000.0", balance)
    if client_id is None:
        start, end = xml.index("<YeshutLakoach>"), xml.index("</YeshutLakoach>") + len("</YeshutLakoach>")
        xml = xml[:start] + xml[end:]
    else:
        xml = xml.replace("987654321", client_id)
    if name:
        xml = xml.replace(
            "</MISPAR-ZIHUY-LAKOACH>",
            f"</MISPAR-ZIHUY-LAKOACH><SHEM-PRATI>{name[0]}</SHEM-PRATI><SHEM-MISHPACHA>{name[1]}</SHEM-MISHPACHA>",
        )
    return xml.encode()


_BULK_KWARGS = dict(
    weight_1=10, weight_3=20, weight_5=25, weight_sharp=35, weight_liquidity=10,
    low_exposure_threshold=25, medium_exposure_threshold=75, bad_hevrot=[],
)


class TestRunBulkComparison:
    @pytest.fixture(autouse=True)
    def _synthetic_universe(self):
        # Mislaka fund codes are numeric: A..D, H become 1..4, 9
        funds = _funds()
        for fund, new_id in zip(funds, ["1", "2", "3", "4", "9"]):
            fund["ID"] = new_id
        with patch.object(service, "load_fund_universe", return_value=_universe(funds)) as loader:
            self.loader = loader
            yield

    def _run(self, files, **overrides):
        return run_bulk_comparison(files, **{**_BULK_KWARGS, **overrides})

    def test_groups_files_by_client(self):
        result = self._run([
            ("a1.xml", _mislaka_xml("111", "XX000004")),
            ("a2.xml", _mislaka_xml("111", "XX000003", "50000.0")),
            ("b.xml", _mislaka_xml("222", "XX000001")),
        ])
        by_id = {c["client_id"]: c for c in result["clients"]}
        assert set(by_id) == {"111", "222"}
        assert by_id["111"]["files"] == ["a1.xml", "a2.xml"]
        assert [h["client"]["id"] for h in by_id["111"]["funds"]] == ["4", "3"]
        assert by_id["111"]["portfolio"]["total_amount"] == 150_000

    def test_portfolio_matches_the_single_client_comparison(self):
        files = [("a1.xml", _mislaka_xml("111", "XX000004")), ("a2.xml", _mislaka_xml("111", "XX000003"))]
        bulk = self._run(files)["clients"][0]
        single = run_comparison([c.decode() for _, c in files], 10, 20, 25, 35, 25, 75, [], weight_liquidity=10)
        assert bulk["funds"] == single["funds"]
        assert bulk["portfolio"] == single["portfolio"]

    def test_most_urgent_client_first(self):
        result = self._run([
            ("best.xml", _mislaka_xml("222", "XX000001")),
            ("worst.xml", _mislaka_xml("111", "XX000004")),
        ])
        assert [c["client_id"] for c in result["clients"]] == ["111", "222"]
        # D -> golden H: 100,000 × (1 + 39.25%) / (1 + 4.25%) − 100,000 (the file's fee is 0.75%)
        assert result["clients"][0]["portfolio"]["upside"]["net"]["1"] == 33573.14

    def test_ties_on_gain_go_to_the_weaker_portfolio_then_unscored_last(self):
        # Scored on the 1-year return alone. Fund 2's client gains by moving to fund 1;
        # fund 1 is already the best; fund 4 is alone in its pool (scored 0, nothing
        # better); fund 3 has no 1-year data (unscored).
        funds = [
            make_fund("1", tsua_1=10.0),
            make_fund("2", tsua_1=5.0),
            make_fund("3", tsua_1=0.0, risk_level="low"),
            make_fund("4", tsua_1=8.0, risk_level="high"),
        ]
        self.loader.return_value = _universe(funds)
        result = self._run([
            ("best.xml", _mislaka_xml("100", "XX000001")),
            ("unscored.xml", _mislaka_xml("300", "XX000003")),
            ("alone.xml", _mislaka_xml("400", "XX000004")),
            ("mover.xml", _mislaka_xml("200", "XX000002")),
        ], weight_1=100, weight_3=0, weight_5=0, weight_sharp=0, weight_liquidity=0)
        assert [c["client_id"] for c in result["clients"]] == ["200", "400", "100", "300"]
        assert [c["portfolio"]["upside"]["net"]["1"] for c in result["clients"]] == [4796.16, 0, 0, 0]
        assert [c["portfolio"]["weighted_score"] for c in result["clients"]] == [0.0, 0.0, 100.0, None]

    def test_file_without_client_id_is_its_own_client(self):
        result = self._run([("x.xml", _mislaka_xml(None, "XX000004")), ("y.xml", _mislaka_xml(None, "XX000003"))])
        assert [(c["client_id"], c["files"]) for c in result["clients"]] == [(None, ["x.xml"]), (None, ["y.xml"])]

    def test_client_name_extracted(self):
        result = self._run([("a.xml", _mislaka_xml("111", name=("ישראל", "ישראלי")))])
        assert result["clients"][0]["client_name"] == "ישראל ישראלי"

    def test_invalid_xml_is_reported(self):
        result = self._run([("broken.xml", b"<nope"), ("ok.xml", _mislaka_xml("111"))])
        assert result["errors"][0]["file"] == "broken.xml"
        assert result["errors"][0]["error"].startswith("הקובץ אינו XML תקין")
        assert len(result["clients"]) == 1

    def test_unreadable_content_is_reported(self):
        # Well-formed XML, but the track code isn't a number
        result = self._run([("weird.xml", _mislaka_xml("111", "XXabcdef"))])
        assert result["errors"][0]["file"] == "weird.xml"
        assert result["errors"][0]["error"].startswith("שגיאה בקריאת הקובץ")

    def test_duplicate_file_skipped(self):
        content = _mislaka_xml("111")
        result = self._run([("x.xml", content), ("copy.xml", content)])
        assert result["clients"][0]["portfolio"]["total_amount"] == 100_000
        assert result["skipped"] == [{"file": "copy.xml", "reason": "כפילות של הקובץ x.xml"}]

    def test_file_without_gemel_funds_skipped(self):
        result = self._run([("pension.xml", _mislaka_xml("111", "XX999999"))])
        assert result["clients"] == []
        assert result["skipped"] == [
            {"file": "pension.xml", "reason": "לא נמצאו בקובץ קופות גמל או השתלמות מגמל נט"}
        ]

    def test_accepts_text_content(self):
        result = self._run([("a.xml", _mislaka_xml("111").decode())])
        assert result["clients"][0]["client_id"] == "111"

    def test_settings_reach_the_universe(self):
        self._run([("a.xml", _mislaka_xml("111"))], bad_hevrot=["X"], israel_share_min=10, israel_share_max=90)
        self.loader.assert_called_once_with(25, 75, ["X"], 10, 90)

    def test_old_callers_without_a_liquidity_weight(self):
        kwargs = {k: v for k, v in _BULK_KWARGS.items() if k != "weight_liquidity"}
        result = run_bulk_comparison([("a.xml", _mislaka_xml("111", "XX000003"))], **{**kwargs, "weight_sharp": 45})
        assert result["clients"][0]["funds"][0]["client"]["grade"] > 0

    def test_files_received_count(self):
        assert self._run([("a.xml", _mislaka_xml("111")), ("b.xml", b"<bad")])["files_received"] == 2
