"""System tests on the real GemeNet data: the production pipeline checked against an oracle.

The oracle below is a separate, deliberately plain re-implementation of the
AmoScore rules that reads the raw XML files itself (no ``src`` parsing code).
Holdings are sampled from across the whole market and every figure the
service returns — pool, rank, grade, alternatives, projections, liquidity,
equity split, golden option, portfolio — is compared with the oracle.

Because expected values are derived from the data files, the tests stay valid
when the data is refreshed.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass

import pytest

from src.comparison.config import GEMEL_NET_PATH, RISKS_MAP_PATH
from src.comparison.service import run_bulk_comparison, run_comparison

pytestmark = pytest.mark.skipif(
    not GEMEL_NET_PATH.exists() or not RISKS_MAP_PATH.exists(),
    reason="Real data files not present",
)

GENERAL_POPULATION = "כלל האוכלוסיה"
WEIGHTS = {"t1": 10, "t3": 20, "t5": 25, "sharpe": 35, "liquidity": 10}
KWARGS = dict(weight_1=10, weight_3=20, weight_5=25, weight_sharp=35, weight_liquidity=10,
              low_exposure_threshold=25, medium_exposure_threshold=75, bad_hevrot=[])
RETURN_TAGS = {"t1": "TSUA_MITZTABERET_LETKUFA", "t3": "TSUA_SHNATIT_MEMUZAAT_3_SHANIM",
               "t5": "TSUA_SHNATIT_MEMUZAAT_5_SHANIM"}
YEARS = {"t1": 1, "t3": 3, "t5": 5}
SUFFIX = {"t1": "", "t3": "_3", "t5": "_5"}


# ---------------------------------------------------------------------------
# Oracle
# ---------------------------------------------------------------------------


@dataclass
class Fund:
    id: str
    sug: str
    population: str
    hevra: str
    returns: dict          # t1/t3/t5 -> float, or None when missing
    sharpe: float | None
    liquidity: float | None
    equity: float | None
    foreign: float | None

    def risk(self, low=25, medium=75):
        if self.equity is None:
            return "invalid"
        return "low" if self.equity <= low else "medium" if self.equity <= medium else "high"

    def israel_share(self):
        if self.equity is None or self.foreign is None or self.equity <= 0:
            return None
        return min(max(self.equity - self.foreign, 0.0), self.equity) / self.equity * 100


def _value(row, tag):
    """A reported number, or None. GemeNet reports "no data" as 0.0 (e.g. self-managed accounts)."""
    text = row.findtext(tag)
    return float(text) if text and float(text) != 0.0 else None


def load_market():
    exposures = {}
    for row in ET.parse(RISKS_MAP_PATH).getroot().findall("Row"):
        kind = {", חשיפה למניות": "equity", 'חשיפה לחו"ל': "foreign"}.get(row.findtext("SHM_SUG_NECHES"))
        if kind:
            exposures.setdefault(int(row.findtext("ID_KUPA")), {})[kind] = float(row.findtext("ACHUZ_SUG_NECHES"))
    market = {}
    for row in ET.parse(GEMEL_NET_PATH).getroot().findall("Row"):
        fund_id = row.findtext("ID").strip()
        assets = float(row.findtext("YITRAT_NCHASIM_LSOF_TKUFA") or 0)
        net = float(row.findtext("TZVIRA_NETO") or 0)
        exp = exposures.get(int(fund_id), {})
        market[fund_id] = Fund(
            id=fund_id,
            sug=row.findtext("SUG_KUPA").strip(),
            population=row.findtext("UCHLUSIYAT_YAAD").strip(),
            hevra=row.findtext("SHM_HEVRA_MENAHELET").strip(),
            returns={k: _value(row, tag) for k, tag in RETURN_TAGS.items()},
            sharpe=_value(row, "SHARP_RIBIT_HASRAT_SIKUN"),
            liquidity=net / assets * 100 if assets > 0 else None,
            equity=exp.get("equity"),
            foreign=exp.get("foreign"),
        )
    return market


def net_return(fund, key, fee):
    """The return after the client's fee — charged on losses as well as gains."""
    value = fund.returns[key]
    return None if value is None else value - fee


def grade_pool(pool, fee):
    """Grade every fund in *pool* the AmoScore way. Returns {id: (grade, has_grade, liquidity_score)}."""
    def minmax(values):
        present = [v for v in values.values() if v is not None]
        lo, hi = (min(present), max(present)) if present else (0, 0)
        return {k: ((v - lo) / (hi - lo) * 100 if hi > lo else 0.0) if v is not None else 0.0
                for k, v in values.items()}

    metrics = {key: {f.id: net_return(f, key, fee) for f in pool} for key in RETURN_TAGS}
    metrics["sharpe"] = {f.id: f.sharpe for f in pool}
    normalised = {key: minmax(values) for key, values in metrics.items()}
    distinct = sorted({f.liquidity for f in pool if f.liquidity is not None})
    liquidity = {f.id: (distinct.index(f.liquidity) / (len(distinct) - 1) * 100 if len(distinct) > 1 else 50.0)
                 if f.liquidity is not None else 0.0 for f in pool}
    normalised["liquidity"] = liquidity
    metrics["liquidity"] = {f.id: f.liquidity for f in pool}

    grades = {}
    for f in pool:
        scorable = all(metrics[k][f.id] is not None for k, w in WEIGHTS.items() if w)
        grade = sum(normalised[k][f.id] * w / 100 for k, w in WEIGHTS.items()) if scorable else 0.0
        grades[f.id] = (grade, scorable, liquidity[f.id])
    return grades


def projection(amount, client, option, key, fee, gross=False):
    client_return = net_return(client, key, fee)
    option_return = option.returns[key] if gross else net_return(option, key, fee)
    if client_return is None or option_return is None:
        return None
    years = YEARS[key]
    return amount * (1 + option_return / 100) ** years / (1 + client_return / 100) ** years


def peers(market, client, risk_level, bad_hevrot=(), share_range=(0, 100)):
    low, high = share_range
    def recommendable(f):
        if f.population != GENERAL_POPULATION or f.hevra in bad_hevrot:
            return False
        if low > 0 or high < 100:
            share = f.israel_share()
            return share is not None and low <= share <= high
        return True
    return [f for f in market.values() if recommendable(f) and f.sug == client.sug and f.risk() == risk_level]


# ---------------------------------------------------------------------------
# Fixtures: a sample of real holdings across the whole market
# ---------------------------------------------------------------------------


FEE = 0.5


def _mislaka(tracks, client_id="987654321"):
    body = "".join(
        f"<PerutMasluleiHashkaa><SCHUM-TZVIRA-BAMASLUL>{amount}</SCHUM-TZVIRA-BAMASLUL>"
        f"<KOD-MASLUL-HASHKAA>XX{int(fund_id):06d}</KOD-MASLUL-HASHKAA>"
        f"<SHEUR-DMEI-NIHUL-HISACHON>{FEE}</SHEUR-DMEI-NIHUL-HISACHON></PerutMasluleiHashkaa>"
        for fund_id, amount in tracks
    )
    return (f"<MislakaRoot><YeshutLakoach><MISPAR-ZIHUY-LAKOACH>{client_id}</MISPAR-ZIHUY-LAKOACH></YeshutLakoach>"
            f"<Mutzar><KOD-MEZAHE-YATZRAN>Y</KOD-MEZAHE-YATZRAN><HeshbonOPolisa><SHEM-TOCHNIT>P</SHEM-TOCHNIT>"
            f"<TAARICH-HITZTARFUT-MUTZAR>20180101</TAARICH-HITZTARFUT-MUTZAR><PirteiTaktziv>{body}</PirteiTaktziv>"
            f"</HeshbonOPolisa></Mutzar></MislakaRoot>")


@pytest.fixture(scope="module")
def market():
    return load_market()


@pytest.fixture(scope="module")
def sample(market):
    """Every 11th classifiable fund (general and special populations, every fund type and risk)."""
    funds = sorted((f for f in market.values() if f.risk() != "invalid"), key=lambda f: int(f.id))
    chosen = funds[::11]
    assert len(chosen) >= 40
    assert {f.risk() for f in chosen} == {"low", "medium", "high"}
    return [(f.id, 10_000.0 + 1_000 * i) for i, f in enumerate(chosen)]


@pytest.fixture(scope="module")
def result(sample):
    return run_comparison(mislaka_file=[_mislaka(sample)], **KWARGS)


@pytest.fixture(scope="module")
def holdings(result):
    return {h["client"]["id"]: h for h in result["funds"]}


def _each(sample, holdings, market):
    for fund_id, amount in sample:
        yield market[fund_id], amount, holdings[fund_id]


# ---------------------------------------------------------------------------
# Per-holding checks against the oracle
# ---------------------------------------------------------------------------


class TestAgainstOracle:
    def test_every_sampled_holding_is_returned(self, sample, holdings):
        assert set(holdings) == {fund_id for fund_id, _ in sample}

    def test_identity_money_and_risk(self, sample, holdings, market):
        for fund, amount, holding in _each(sample, holdings, market):
            client = holding["client"]
            assert (client["client_id"], client["amount"], client["dmei_nihul"]) == ("987654321", amount, FEE)
            assert client["risk_level"] == fund.risk(), fund.id
            assert client["hevra"] == fund.hevra

    def test_pool_size_rank_and_percentile(self, sample, holdings, market):
        for fund, _, holding in _each(sample, holdings, market):
            pool = peers(market, fund, fund.risk())
            size = len(pool) + (0 if fund in pool else 1)
            client = holding["client"]
            assert client["total_in_risk"] == size, fund.id
            assert client["percentile"] == round((size - client["rank"]) / size * 100)

    def test_grade_and_liquidity_score(self, sample, holdings, market):
        for fund, _, holding in _each(sample, holdings, market):
            pool = peers(market, fund, fund.risk())
            grades = grade_pool(pool if fund in pool else [fund, *pool], FEE)
            grade, scorable, liquidity_score = grades[fund.id]
            client = holding["client"]
            assert client["grade"] == pytest.approx(grade, abs=0.011), fund.id
            assert client["has_grade"] is scorable, fund.id
            if fund.liquidity is not None:
                assert client["liquidity_index"] == pytest.approx(fund.liquidity, abs=0.006)
                assert client["liquidity_score"] == pytest.approx(liquidity_score, abs=0.051)

    def test_client_rank_counts_better_graded_peers(self, sample, holdings, market):
        for fund, _, holding in _each(sample, holdings, market):
            pool = peers(market, fund, fund.risk())
            grades = grade_pool(pool if fund in pool else [fund, *pool], FEE)
            own = grades[fund.id][0]
            strictly_better = sum(1 for fid, (g, _, _) in grades.items() if fid != fund.id and g > own + 0.011)
            not_worse = sum(1 for fid, (g, _, _) in grades.items() if fid != fund.id and g >= own - 0.011)
            assert strictly_better + 1 <= holding["client"]["rank"] <= not_worse + 1, fund.id

    def test_alternatives_are_the_top_graded_other_peers(self, sample, holdings, market):
        for fund, _, holding in _each(sample, holdings, market):
            pool = peers(market, fund, fund.risk())
            grades = grade_pool(pool if fund in pool else [fund, *pool], FEE)
            others = sorted((g for fid, (g, _, _) in grades.items() if fid != fund.id), reverse=True)
            reported = [a["grade"] for a in holding["alternatives"]]
            assert reported == pytest.approx(others[:3], abs=0.011), fund.id
            for alt in holding["alternatives"]:
                assert market[alt["id"]] in pool
                assert alt["grade"] == pytest.approx(grades[alt["id"]][0], abs=0.011)

    def test_returns_and_equity_split_of_alternatives(self, sample, holdings, market):
        for fund, _, holding in _each(sample, holdings, market):
            for alt in holding["alternatives"]:
                option = market[alt["id"]]
                for key in RETURN_TAGS:
                    tsua = f"tsua_{YEARS[key]}"
                    assert alt["gross"][tsua] == pytest.approx(option.returns[key] or 0.0, abs=0.006)
                    assert alt[tsua] == pytest.approx(net_return(option, key, FEE) or 0.0, abs=0.006)
                share = option.israel_share()
                assert alt["israel_equity_share"] == (pytest.approx(share, abs=0.051) if share is not None else None)

    def test_projections(self, sample, holdings, market):
        for fund, amount, holding in _each(sample, holdings, market):
            for alt in holding["alternatives"]:
                option = market[alt["id"]]
                for key in RETURN_TAGS:
                    for figures, gross in ((alt, False), (alt["gross"], True)):
                        expected = projection(amount, fund, option, key, FEE, gross)
                        actual = figures[f"potential_amount{SUFFIX[key]}"]
                        if expected is None:
                            assert actual is None, (fund.id, alt["id"], key)
                        else:
                            assert actual == pytest.approx(expected, abs=0.011), (fund.id, alt["id"], key)

    def test_golden_option(self, sample, holdings, market):
        offered = 0
        for fund, amount, holding in _each(sample, holdings, market):
            golden = holding["golden"]
            high = peers(market, fund, "high")
            if fund.risk() == "high" or not high:
                assert golden == {}, fund.id
                continue
            grades = grade_pool(high, FEE)
            top = max(g for g, _, _ in grades.values())
            best_same = holding["alternatives"][0] if holding["alternatives"] else None
            same_potential = projection(amount, fund, market[best_same["id"]], "t1", FEE) if best_same else None
            if golden:
                offered += 1
                assert golden["grade"] == pytest.approx(top, abs=0.011), fund.id
                gold_potential = projection(amount, fund, market[golden["id"]], "t1", FEE)
                assert gold_potential is not None
                assert same_potential is None or gold_potential > same_potential
            else:
                tops = [fid for fid, (g, _, _) in grades.items() if g >= top - 0.011]
                for fid in tops:
                    gold_potential = projection(amount, fund, market[fid], "t1", FEE)
                    assert gold_potential is None or (
                        same_potential is not None and gold_potential <= same_potential + 0.01
                    ), fund.id
        assert offered > 0

    def test_portfolio(self, result, sample, market):
        holdings = result["funds"]
        graded = [h for h in holdings if h["client"]["has_grade"]]
        money = sum(h["client"]["amount"] for h in graded)
        expected = sum(h["client"]["grade"] * h["client"]["amount"] for h in graded) / money
        portfolio = result["portfolio"]
        assert portfolio["weighted_score"] == pytest.approx(expected, abs=0.05)
        assert portfolio["total_amount"] == pytest.approx(sum(a for _, a in sample))
        assert portfolio["coverage"] == pytest.approx(money / portfolio["total_amount"] * 100, abs=0.05)


# ---------------------------------------------------------------------------
# Settings, against the oracle
# ---------------------------------------------------------------------------


class TestSettings:
    @pytest.fixture(scope="class")
    def medium_fund(self, market):
        return next(f for f in sorted(market.values(), key=lambda f: int(f.id))
                    if f.population == GENERAL_POPULATION and f.risk() == "medium"
                    and all(v is not None for v in f.returns.values()) and f.sharpe and f.liquidity is not None)

    def _run(self, fund, **overrides):
        return run_comparison(mislaka_file=[_mislaka([(fund.id, 100_000.0)])], **{**KWARGS, **overrides})["funds"][0]

    def test_excluded_company_shrinks_the_pool_by_its_funds(self, market, medium_fund):
        normal = self._run(medium_fund)
        excluded = normal["alternatives"][0]["hevra"]
        filtered = self._run(medium_fund, bad_hevrot=[excluded])
        expected = len(peers(market, medium_fund, "medium", bad_hevrot=[excluded]))
        expected += 0 if medium_fund.hevra != excluded else 1
        assert filtered["client"]["total_in_risk"] == expected
        assert all(a["hevra"] != excluded for a in filtered["alternatives"])
        assert filtered["golden"] == {} or filtered["golden"]["hevra"] != excluded

    def test_israel_share_range(self, market, medium_fund):
        filtered = self._run(medium_fund, israel_share_min=50, israel_share_max=100)
        pool = peers(market, medium_fund, "medium", share_range=(50, 100))
        assert filtered["client"]["total_in_risk"] == len(pool) + (0 if medium_fund in pool else 1)
        for option in filtered["alternatives"] + ([filtered["golden"]] if filtered["golden"] else []):
            assert 50 <= option["israel_equity_share"] <= 100

    def test_override_risk_level(self, market, medium_fund):
        overridden = self._run(medium_fund, override_risk_level="high")
        assert overridden["client"]["risk_level"] == "medium"
        assert overridden["client"]["total_in_risk"] == len(peers(market, medium_fund, "high")) + 1
        assert all(market[a["id"]].risk() == "high" for a in overridden["alternatives"])
        assert overridden["golden"] == {}

    def test_custom_thresholds(self, market, medium_fund):
        result = self._run(medium_fund, low_exposure_threshold=0, medium_exposure_threshold=100)
        expected = "medium" if medium_fund.equity <= 100 else "high"
        assert result["client"]["risk_level"] == expected
        assert all(0 < market[a["id"]].equity <= 100 for a in result["alternatives"])

    def test_fee_level_does_not_change_the_ranking(self, medium_fund):
        # 103's pool includes 818, which lost 1.3% over a year: it must pay the fee like everyone else
        cheap = run_comparison(mislaka_file=[_mislaka([(medium_fund.id, 100_000.0)]).replace(">0.5<", ">0.1<")],
                               **KWARGS)["funds"][0]
        pricey = self._run(medium_fund)
        assert cheap["client"]["rank"] == pricey["client"]["rank"]
        assert [a["id"] for a in cheap["alternatives"]] == [a["id"] for a in pricey["alternatives"]]


class TestBulk:
    def test_bulk_matches_single_client_runs(self, sample):
        files = [(f"c{i}.xml", _mislaka(sample[i::4], client_id=f"10000000{i}").encode()) for i in range(4)]
        bulk = run_bulk_comparison(files, **KWARGS)
        assert len(bulk["clients"]) == 4
        for client in bulk["clients"]:
            i = int(client["client_id"][-1])
            single = run_comparison(mislaka_file=[_mislaka(sample[i::4], client_id=client["client_id"])], **KWARGS)
            assert client["funds"] == single["funds"]
            assert client["portfolio"] == single["portfolio"]
        upsides = [c["portfolio"]["upside"]["net"]["1"] for c in bulk["clients"]]
        assert upsides == sorted(upsides, reverse=True)
