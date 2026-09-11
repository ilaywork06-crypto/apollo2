"""Integration tests: the real pipeline, from XML files to results, on a small hand-made market.

GemeNet and risk-map files are written to a temp dir and the service is pointed
at them, so parsing, risk classification, filtering, fees, grading, liquidity,
projections and the portfolio summary all run together. Every expected number
below is worked out by hand from the fixture data.

The market (all "תגמולים" unless noted; returns are 1Y/3Y/5Y, liquidity = net
accumulation / assets):

    ID   company  equity foreign  returns     Sharpe  liquidity  risk (25/75)
    101  Alpha    80     50       20/15/12    2.0     50/500=10%  high
    102  Beta     90     10       25/14/11    1.8     10/1000=1%  high
    103  Gamma    50     30       12/9/8      1.5     -20/400=-5% medium
    104  Delta    45     45       10/8/7      1.2     30/300=10%  medium
    105  Eps      60     20       14/10/9     1.7     5/100=5%    medium
    106  Zeta     55     5        30/20/18    3.0     -           medium, special population
    107  Theta    50     10       40/30/25    3.0     -           medium, השתלמות
    108  Iota     10     5        4/3/2       0.5     -           low
"""

import pytest

from src.comparison import service
from src.comparison.service import run_bulk_comparison, run_comparison

_FUNDS = [
    # id, name, company, population, sug, 1y, 3y, 5y, sharpe, net_accumulation, assets
    ("101", "Alpha Growth", "Alpha", "כלל האוכלוסיה", "תגמולים ואישית לפיצויים", 20, 15, 12, 2.0, 50, 500),
    ("102", "Beta Growth", "Beta", "כלל האוכלוסיה", "תגמולים ואישית לפיצויים", 25, 14, 11, 1.8, 10, 1000),
    ("103", "Gamma Mixed", "Gamma", "כלל האוכלוסיה", "תגמולים ואישית לפיצויים", 12, 9, 8, 1.5, -20, 400),
    ("104", "Delta Mixed", "Delta", "כלל האוכלוסיה", "תגמולים ואישית לפיצויים", 10, 8, 7, 1.2, 30, 300),
    ("105", "Eps Mixed", "Eps", "כלל האוכלוסיה", "תגמולים ואישית לפיצויים", 14, 10, 9, 1.7, 5, 100),
    ("106", "Zeta Special", "Zeta", "עובדי מדינה", "תגמולים ואישית לפיצויים", 30, 20, 18, 3.0, 1, 10),
    ("107", "Theta Hishtalmut", "Theta", "כלל האוכלוסיה", "קרנות השתלמות", 40, 30, 25, 3.0, 1, 10),
    ("108", "Iota Bonds", "Iota", "כלל האוכלוסיה", "תגמולים ואישית לפיצויים", 4, 3, 2, 0.5, 1, 10),
]
_EXPOSURES = {"101": (80, 50), "102": (90, 10), "103": (50, 30), "104": (45, 45), "105": (60, 20),
              "106": (55, 5), "107": (50, 10), "108": (10, 5)}
_DEFAULTS = dict(weight_1=10, weight_3=20, weight_5=25, weight_sharp=35, weight_liquidity=10,
                 low_exposure_threshold=25, medium_exposure_threshold=75, bad_hevrot=[])


def _gemel_net_xml():
    rows = "".join(
        f"""<Row><ID>{i}</ID><SHM_KUPA>{name}</SHM_KUPA><SUG_KUPA>{sug}</SUG_KUPA>
        <SHM_HEVRA_MENAHELET>{company}</SHM_HEVRA_MENAHELET><UCHLUSIYAT_YAAD>{population}</UCHLUSIYAT_YAAD>
        <TSUA_MITZTABERET_LETKUFA>{t1}</TSUA_MITZTABERET_LETKUFA>
        <TSUA_SHNATIT_MEMUZAAT_3_SHANIM>{t3}</TSUA_SHNATIT_MEMUZAAT_3_SHANIM>
        <TSUA_SHNATIT_MEMUZAAT_5_SHANIM>{t5}</TSUA_SHNATIT_MEMUZAAT_5_SHANIM>
        <SHARP_RIBIT_HASRAT_SIKUN>{sharpe}</SHARP_RIBIT_HASRAT_SIKUN>
        <TZVIRA_NETO>{net}</TZVIRA_NETO><YITRAT_NCHASIM_LSOF_TKUFA>{assets}</YITRAT_NCHASIM_LSOF_TKUFA></Row>"""
        for i, name, company, population, sug, t1, t3, t5, sharpe, net, assets in _FUNDS
    )
    return f"<ROWSET>{rows}</ROWSET>"


def _risks_xml():
    rows = "".join(
        f"""<Row><ID_KUPA>{i}</ID_KUPA><SHM_SUG_NECHES>, חשיפה למניות</SHM_SUG_NECHES><ACHUZ_SUG_NECHES>{eq}</ACHUZ_SUG_NECHES></Row>
        <Row><ID_KUPA>{i}</ID_KUPA><SHM_SUG_NECHES>חשיפה לחו"ל</SHM_SUG_NECHES><ACHUZ_SUG_NECHES>{fx}</ACHUZ_SUG_NECHES></Row>"""
        for i, (eq, fx) in _EXPOSURES.items()
    )
    return f"<ROWSET>{rows}</ROWSET>"


def _mislaka(client_id, *tracks):
    body = "".join(
        f"""<PerutMasluleiHashkaa><SCHUM-TZVIRA-BAMASLUL>{amount}</SCHUM-TZVIRA-BAMASLUL>
        <KOD-MASLUL-HASHKAA>XX000{fund_id}</KOD-MASLUL-HASHKAA>
        <SHEUR-DMEI-NIHUL-HISACHON>{fee}</SHEUR-DMEI-NIHUL-HISACHON></PerutMasluleiHashkaa>"""
        for fund_id, amount, fee in tracks
    )
    return f"""<MislakaRoot><YeshutLakoach><MISPAR-ZIHUY-LAKOACH>{client_id}</MISPAR-ZIHUY-LAKOACH></YeshutLakoach>
    <Mutzar><KOD-MEZAHE-YATZRAN>Y</KOD-MEZAHE-YATZRAN><HeshbonOPolisa><SHEM-TOCHNIT>Plan</SHEM-TOCHNIT>
    <TAARICH-HITZTARFUT-MUTZAR>20180101</TAARICH-HITZTARFUT-MUTZAR><PirteiTaktziv>{body}</PirteiTaktziv>
    </HeshbonOPolisa></Mutzar></MislakaRoot>"""


# Client: ₪100,000 in 104 (fee 0.5%) and ₪50,000 in 102 (fee 0.25%)
CLIENT = _mislaka("039485721", ("104", "100000.0", "0.5"), ("102", "50000.0", "0.25"))


@pytest.fixture(autouse=True)
def market(tmp_path, monkeypatch):
    (tmp_path / "funds.xml").write_text(_gemel_net_xml(), encoding="utf-8")
    (tmp_path / "risks.xml").write_text(_risks_xml(), encoding="utf-8")
    monkeypatch.setattr(service, "GEMEL_NET_PATH", tmp_path / "funds.xml")
    monkeypatch.setattr(service, "RISKS_MAP_PATH", tmp_path / "risks.xml")


def _run(files=(CLIENT,), **overrides):
    return run_comparison(mislaka_file=list(files), **{**_DEFAULTS, **overrides})


def _holding(result, fund_id):
    return next(h for h in result["funds"] if h["client"]["id"] == fund_id)


class TestMediumRiskHolding:
    """104's peers: 103, 104, 105 (106 is a special population, 107 another fund type).

    Net of 0.5%: 103 11.5/8.5/7.5, 104 9.5/7.5/6.5, 105 13.5/9.5/8.5.
    Normalised — returns: 105 100, 103 50, 104 0; Sharpe: 105 100, 103 60, 104 0;
    liquidity rank: 104 100, 105 50, 103 0.
    Grades: 105 95.0, 103 48.5, 104 10.0.
    """

    def test_rank_and_pool(self):
        client = _holding(_run(), "104")["client"]
        assert (client["grade"], client["rank"], client["total_in_risk"], client["percentile"]) == (10.0, 3, 3, 0)
        assert (client["risk_level"], client["tsua_1"], client["liquidity_index"], client["liquidity_score"]) == (
            "medium", 9.5, 10.0, 100.0)

    def test_alternatives(self):
        alternatives = _holding(_run(), "104")["alternatives"]
        assert [(a["id"], a["grade"], a["rank"]) for a in alternatives] == [("105", 95.0, 1), ("103", 48.5, 2)]

    def test_projections_to_the_best_alternative(self):
        best = _holding(_run(), "104")["alternatives"][0]
        # 100,000 × (1.135/1.095), (1.095/1.075)^3, (1.085/1.065)^5
        assert (best["potential_amount"], best["potential_amount_3"], best["potential_amount_5"]) == (
            103652.97, 105685.88, 109749.02)
        assert best["gross"]["tsua_1"] == 14.0

    def test_golden_option(self):
        golden = _holding(_run(), "104")["golden"]
        # High-risk grades: 101 90.0, 102 10.0. 101 over a year: 100,000 × 1.195/1.095 beats 105's 103,652.97
        assert (golden["id"], golden["grade"], golden["potential_amount"]) == ("101", 90.0, 109132.42)

    def test_equity_split(self):
        holding = _holding(_run(), "104")
        assert (holding["client"]["israel_equity_exposure"], holding["client"]["israel_equity_share"]) == (0.0, 0.0)
        assert [a["israel_equity_share"] for a in holding["alternatives"]] == [66.7, 40.0]


class TestHighRiskHolding:
    def test_two_fund_pool_without_golden(self):
        holding = _holding(_run(), "102")
        assert (holding["client"]["grade"], holding["client"]["rank"], holding["client"]["total_in_risk"]) == (10.0, 2, 2)
        assert [a["id"] for a in holding["alternatives"]] == ["101"]
        assert holding["golden"] == {}

    def test_better_graded_fund_can_still_lose_money_over_one_year(self):
        best = _holding(_run(), "102")["alternatives"][0]
        # 101 has a better AmoScore but a lower 1-year return: 50,000 × 1.1975/1.2475
        assert (best["potential_amount"], best["diff"]) == (47995.99, -2004.01)


class TestPortfolio:
    def test_money_weighted_scores_and_upside(self):
        portfolio = _run()["portfolio"]
        assert portfolio["total_amount"] == 150_000.0
        assert portfolio["weighted_score"] == 10.0
        # (95 × 100,000 + 90 × 50,000) / 150,000
        assert portfolio["potential_score"] == 93.3
        # Only 104 gains over a year (via the golden 101); 102's best move loses money
        assert portfolio["upside"]["net"]["1"] == 9132.42


class TestSettings:
    def test_excluded_company_is_never_suggested(self):
        holding = _holding(_run(bad_hevrot=["Eps"]), "104")
        assert [a["id"] for a in holding["alternatives"]] == ["103"]
        assert holding["client"]["total_in_risk"] == 2

    def test_israel_share_range(self):
        # Israeli share of equity: 101 37.5%, 102 88.9%, 103 40%, 104 0%, 105 66.7%
        holding = _holding(_run(israel_share_min=0, israel_share_max=40), "104")
        assert [a["id"] for a in holding["alternatives"]] == ["103"]
        assert holding["golden"]["id"] == "101"

    def test_override_risk_level(self):
        holding = _holding(_run(override_risk_level="high"), "104")
        assert holding["client"]["total_in_risk"] == 3
        assert {a["id"] for a in holding["alternatives"]} == {"101", "102"}
        assert holding["golden"] == {}

    def test_custom_thresholds_move_funds_between_pools(self):
        # At 50/85: 103, 104, 108 low; 101, 105 medium; 102 high
        holding = _holding(_run(low_exposure_threshold=50, medium_exposure_threshold=85), "104")
        assert holding["client"]["risk_level"] == "low"
        assert holding["client"]["total_in_risk"] == 3
        assert {a["id"] for a in holding["alternatives"]} == {"103", "108"}

    def test_without_the_liquidity_weight_the_weakest_fund_scores_zero(self):
        client = _holding(_run(weight_sharp=45, weight_liquidity=0), "104")["client"]
        assert (client["grade"], client["has_grade"]) == (0.0, True)

    def test_special_population_fund_is_ranked_but_never_suggested(self):
        holding = _holding(_run([_mislaka("1", ("106", "10000.0", "0.5"))]), "106")
        assert holding["client"]["total_in_risk"] == 4
        assert holding["client"]["rank"] == 1
        assert "106" not in [a["id"] for a in holding["alternatives"]]


class TestBulk:
    def test_clients_ranked_by_gain(self):
        stays = _mislaka("111", ("105", "80000.0", "0.5"))
        result = run_bulk_comparison([("stays.xml", stays.encode()), ("moves.xml", CLIENT.encode())], **_DEFAULTS)
        assert [c["client_id"] for c in result["clients"]] == ["039485721", "111"]
        assert result["clients"][0]["portfolio"] == _run()["portfolio"]
