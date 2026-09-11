"""Orchestrates fund comparisons for one client's Mislaka files or for many clients at once."""

import hashlib
from dataclasses import dataclass

import lxml.etree as ET

from src.comparison.config import (
    DEFAULT_WEIGHT_1,
    DEFAULT_WEIGHT_3,
    DEFAULT_WEIGHT_5,
    DEFAULT_WEIGHT_LIQUIDITY,
    DEFAULT_WEIGHT_SHARP,
    GEMEL_NET_PATH,
    RISKS_MAP_PATH,
)
from src.comparison.filters import filter_by_israel_equity_share, remove_bad_hevrot
from src.comparison.grading import calculate_grade
from src.comparison.matching import find_matching_funds, get_funds_by_risk_level
from src.comparison.normalization import has_metric
from src.comparison.pool import build_graded_pool
from src.comparison.portfolio import summarize_portfolio
from src.comparison.projections import calculate_potential_amount
from src.comparison.ranking import get_client_ranking
from src.comparison.risk_classifier import RiskClassifier
from src.parsers.fund_parser import parse_xml_file
from src.parsers.mislaka.parser import parse_mislaka_file, parse_multible_mislaka_files
from src.parsers.mislaka.track_extractor import MIN_TRACK_BALANCE

GENERAL_POPULATION = "כלל האוכלוסיה"

# (years, return field, response-key suffix) for each projection horizon
_HORIZONS = (
    (1, "tsua_mitztaberet_letkufa", ""),
    (3, "tsua_3", "_3"),
    (5, "tsua_5", "_5"),
)
_FIELD_BY_YEARS = {years: field for years, field, _ in _HORIZONS}


@dataclass(frozen=True)
class Weights:
    """AmoScore weights in percent; grades are only computed when they sum to 100."""

    one_year: int
    three_year: int
    five_year: int
    sharpe: int
    liquidity: int = 0

    def as_args(self) -> tuple[int, int, int, int, int]:
        return (self.one_year, self.three_year, self.five_year, self.sharpe, self.liquidity)


DEFAULT_WEIGHTS = Weights(
    DEFAULT_WEIGHT_1, DEFAULT_WEIGHT_3, DEFAULT_WEIGHT_5, DEFAULT_WEIGHT_SHARP, DEFAULT_WEIGHT_LIQUIDITY
)


@dataclass(frozen=True)
class FundUniverse:
    """Every GemeNet fund (to match holdings against) and the subset that may be recommended."""

    all_funds: list[dict]
    suggestable: list[dict]


def load_fund_universe(
    low_exposure_threshold: float,
    medium_exposure_threshold: float,
    bad_hevrot: list[str],
    israel_share_min: float = 0.0,
    israel_share_max: float = 100.0,
) -> FundUniverse:
    """Parse the GemeNet data and split it into all funds and recommendable funds.

    A fund may be recommended when it is open to the general population, its
    managing company isn't excluded, and its Israeli equity share lies within
    the requested range.
    """
    risk_classifier = RiskClassifier(path=RISKS_MAP_PATH)
    all_funds = parse_xml_file(
        GEMEL_NET_PATH, low_exposure_threshold, medium_exposure_threshold,
        risk_classifier=risk_classifier, remove_special_cases=False,
    )
    suggestable = [f for f in all_funds if f["UCHLUSIYAT_YAAD"] == GENERAL_POPULATION]
    suggestable = remove_bad_hevrot(suggestable, bad_hevrot)
    suggestable = filter_by_israel_equity_share(suggestable, israel_share_min, israel_share_max)
    return FundUniverse(all_funds=all_funds, suggestable=suggestable)


class _PoolCache:
    """Memoises graded peer pools for the lifetime of one comparison run.

    Holdings sharing a fund type, comparison risk level and management fee are
    graded against the very same pool — very common across many clients — so
    each pool is built once. Cached pools are shared: treat them as read-only.
    """

    def __init__(self, weights: Weights) -> None:
        self._weights = weights
        self._pools: dict[tuple, list[dict]] = {}

    def graded(self, key: tuple, funds: list[dict], fee: float) -> list[dict]:
        cache_key = (*key, fee)
        if cache_key not in self._pools:
            self._pools[cache_key] = build_graded_pool(funds, fee, *self._weights.as_args())
        return self._pools[cache_key]


def _returns(fund: dict, gross: bool = False) -> dict:
    suffix = "_gross" if gross else ""
    return {f"tsua_{years}": round(fund[f"{field}{suffix}"], 2) for years, field, _ in _HORIZONS}


def _potential(
    money: float, client_fund: dict, option: dict, years: int, gross: bool = False
) -> float | None:
    """Project the balance had the client been in *option*, or ``None`` without data on both sides.

    The client's own return is always net of their management fee; the
    option's return is net of the same fee, or gross when *gross* is set.
    """
    field = _FIELD_BY_YEARS[years]
    option_field = f"{field}_gross" if gross else field
    if not has_metric(client_fund, field) or not has_metric(option, option_field):
        return None
    return calculate_potential_amount(
        money, client_fund, option, field=field, years=years, better_field=option_field
    )


def _projections(money: float, client_fund: dict, option: dict, gross: bool) -> dict:
    result = {}
    for years, _, suffix in _HORIZONS:
        potential = _potential(money, client_fund, option, years, gross)
        result[f"potential_amount{suffix}"] = potential
        result[f"diff{suffix}"] = round(potential - money, 2) if potential is not None else None
        result[f"diff_percent{suffix}"] = (
            round((potential - money) / money * 100, 1) if potential is not None else None
        )
    return result


def _profile(fund: dict) -> dict:
    """Equity-geography and liquidity details shown next to a fund."""
    liquidity = fund.get("liquidity_index")
    return {
        "equity_exposure": fund.get("equity_exposure"),
        "foreign_exposure": fund.get("foreign_exposure"),
        "israel_equity_exposure": fund.get("israel_equity_exposure"),
        "israel_equity_share": fund.get("israel_equity_share"),
        "liquidity_index": round(liquidity, 2) if liquidity is not None else None,
        "liquidity_score": (
            round(fund["liquidity_index_normalized"], 1) if liquidity is not None else None
        ),
    }


def _describe_option(option: dict, rank: int, money: float, client_fund: dict) -> dict:
    """Build the payload for a recommended fund.

    Top-level returns and projections assume the client keeps paying their
    current management fee in the new fund; the ``gross`` sub-dict holds the
    same figures without any management fee on the new fund.
    """
    return {
        "name": option["fund_name"],
        "id": option["ID"],
        "grade": option["grade"],
        "has_grade": option["has_grade"],
        "rank": rank,
        "hevra": option["hevra"],
        **_returns(option),
        **_projections(money, client_fund, option, gross=False),
        "gross": {
            **_returns(option, gross=True),
            **_projections(money, client_fund, option, gross=True),
        },
        **_profile(option),
    }


def compare_holding(
    mislaka: dict,
    fund: dict,
    universe: FundUniverse,
    weights: Weights,
    override_risk_level: str | None = None,
    pools: _PoolCache | None = None,
) -> dict | None:
    """Compare one Mislaka holding against its peers.

    The holding's fund is graded among recommendable funds of the same type
    and risk level (or *override_risk_level*), after deducting the client's
    management fee from every fund. The client's own fund always takes part in
    the ranking, even when it could not be recommended itself.

    Args:
        mislaka: The parsed Mislaka track record for the holding.
        fund: The GemeNet record of the holding's fund.
        universe: All funds and the recommendable subset.
        weights: AmoScore weights.
        override_risk_level: Compare against this risk level instead of the
            fund's own; disables the golden option.
        pools: Graded-pool cache shared across the holdings of one run.

    Returns:
        A dict with ``client``, ``alternatives`` (the top three other funds)
        and ``golden`` (the best high-risk fund when it beats the best
        same-risk one, else ``{}``), or ``None`` for a negligible balance.
    """
    money = mislaka["TOTAL-CHISACHON-MTZBR"]
    if money < MIN_TRACK_BALANCE:
        return None
    if pools is None:
        pools = _PoolCache(weights)

    sug = fund["SUG"]
    risk_level = fund["risk_level"]
    comparison_risk_level = override_risk_level or risk_level
    dmey_nihul = mislaka["SHEUR-DMEI-NIHUL-TZVIRA"]
    same_type = [f for f in universe.suggestable if f["SUG"] == sug]

    peers = get_funds_by_risk_level(same_type, comparison_risk_level)
    added_client_fund = None
    if not any(f["ID"] == fund["ID"] for f in peers):
        peers = [fund] + peers
        added_client_fund = fund["ID"]
    sorted_funds = pools.graded((sug, comparison_risk_level, added_client_fund), peers, dmey_nihul)
    client_ranking, total_funds = get_client_ranking(sorted_funds, fund["ID"])
    client_fund = sorted_funds[client_ranking - 1]

    client = {
        "name": client_fund["fund_name"],
        "id": client_fund["ID"],
        "client_id": mislaka.get("MISPAR-ZIHUY-LAKOACH", "unknown"),
        "client_name": mislaka.get("SHEM-LAKOACH", ""),
        "grade": client_fund["grade"],
        "has_grade": client_fund["has_grade"],
        "default_grade": calculate_grade(client_fund, *DEFAULT_WEIGHTS.as_args()),
        "rank": client_ranking,
        "total_in_risk": total_funds,
        "risk_level": risk_level,
        "amount": money,
        "dmei_nihul": dmey_nihul,
        **_returns(client_fund),
        "hevra": client_fund["hevra"],
        "seniority_date": mislaka["TAARICH-HITZTARFUT-MUTZAR"],
        "percentile": round((total_funds - client_ranking) / total_funds * 100),
        **_profile(client_fund),
    }

    golden = {}
    if override_risk_level is None and risk_level != "high":
        high_peers = get_funds_by_risk_level(same_type, "high")
        if high_peers:
            better_gold = pools.graded((sug, "high", None), high_peers, dmey_nihul)[0]
            gold_potential = _potential(money, client_fund, better_gold, 1)
            best_same_risk = next((f for f in sorted_funds if f["ID"] != client_fund["ID"]), None)
            same_risk_potential = (
                _potential(money, client_fund, best_same_risk, 1) if best_same_risk else None
            )
            if gold_potential is not None and (
                same_risk_potential is None or gold_potential > same_risk_potential
            ):
                golden = _describe_option(better_gold, 1, money, client_fund)

    alternatives = []
    for position, option in enumerate(sorted_funds, start=1):
        if len(alternatives) >= 3:
            break
        if option["ID"] != client_fund["ID"]:
            alternatives.append(_describe_option(option, position, money, client_fund))

    return {"client": client, "alternatives": alternatives, "golden": golden}


def run_comparison(
    mislaka_file: list[str],
    weight_1: int,
    weight_3: int,
    weight_5: int,
    weight_sharp: int,
    low_exposure_threshold: float,
    medium_exposure_threshold: float,
    bad_hevrot: list[str],
    override_risk_level: str | None = None,
    weight_liquidity: int = 0,
    israel_share_min: float = 0.0,
    israel_share_max: float = 100.0,
) -> dict:
    """Orchestrate the full fund comparison for all holdings in the Mislaka files.

    Args:
        mislaka_file: List of decoded Mislaka XML file strings.
        weight_1: Weight for the 1-year cumulative return metric.
        weight_3: Weight for the 3-year average annual return metric.
        weight_5: Weight for the 5-year average annual return metric.
        weight_sharp: Weight for the Sharpe ratio metric.
        low_exposure_threshold: Highest equity exposure of a low-risk fund.
        medium_exposure_threshold: Highest equity exposure of a medium-risk fund.
        bad_hevrot: Managing companies never to recommend.
        override_risk_level: Compare every holding against this risk level.
        weight_liquidity: Weight for the liquidity index metric.
        israel_share_min: Lowest Israeli share of the equity, in percent, for a
            fund to be recommended.
        israel_share_max: Highest Israeli share of the equity, in percent.

    Returns:
        A dict with a ``funds`` key containing a list of per-holding result
        dicts (see :func:`compare_holding`) and a ``portfolio`` key with the
        money-weighted summary (see
        :func:`src.comparison.portfolio.summarize_portfolio`).
    """
    weights = Weights(weight_1, weight_3, weight_5, weight_sharp, weight_liquidity)
    universe = load_fund_universe(
        low_exposure_threshold, medium_exposure_threshold, bad_hevrot,
        israel_share_min, israel_share_max,
    )
    pools = _PoolCache(weights)
    mislaka_list = parse_multible_mislaka_files(mislaka_file)
    funds_list = []
    for mislaka, fund in find_matching_funds(mislaka_list, universe.all_funds):
        holding = compare_holding(mislaka, fund, universe, weights, override_risk_level, pools)
        if holding is not None:
            funds_list.append(holding)
    return {"funds": funds_list, "portfolio": summarize_portfolio(funds_list)}


def _describe_parse_error(exc: Exception) -> str:
    if isinstance(exc, ET.XMLSyntaxError):
        return f"הקובץ אינו XML תקין ({exc})"
    return f"שגיאה בקריאת הקובץ ({exc})"


def _urgency_key(client: dict) -> tuple:
    """Sort key: biggest 1-year gain from moving first, then the weakest portfolio."""
    portfolio = client["portfolio"]
    score = portfolio["weighted_score"]
    return (-portfolio["upside"]["net"]["1"], score if score is not None else 101)


def run_bulk_comparison(
    files: list[tuple[str, bytes | str]],
    weight_1: int,
    weight_3: int,
    weight_5: int,
    weight_sharp: int,
    low_exposure_threshold: float,
    medium_exposure_threshold: float,
    bad_hevrot: list[str],
    override_risk_level: str | None = None,
    weight_liquidity: int = 0,
    israel_share_min: float = 0.0,
    israel_share_max: float = 100.0,
) -> dict:
    """Compare the holdings of many clients at once and rank them by urgency to move.

    Files are grouped by the client ID inside them; a file without one is
    treated as its own client. The fund data is parsed once and graded pools
    are shared across every holding, so large batches stay fast. One bad file
    never aborts the batch: unreadable files are listed in ``errors``, and
    files that are exact duplicates or hold no GemeNet funds (e.g. pension
    funds or insurance policies) are listed in ``skipped``.

    Args:
        files: ``(file name, content)`` pairs of Mislaka XML documents.
        Remaining arguments: as for :func:`run_comparison`.

    Returns:
        A dict with ``clients`` — each with ``client_id`` (``None`` when the
        file has none), ``client_name``, ``files``, ``funds`` (per-holding
        results) and ``portfolio`` (see
        :func:`src.comparison.portfolio.summarize_portfolio`), most urgent
        first — plus ``errors``, ``skipped`` and ``files_received``.
    """
    weights = Weights(weight_1, weight_3, weight_5, weight_sharp, weight_liquidity)
    universe = load_fund_universe(
        low_exposure_threshold, medium_exposure_threshold, bad_hevrot,
        israel_share_min, israel_share_max,
    )
    pools = _PoolCache(weights)
    clients: dict[str, dict] = {}
    errors: list[dict] = []
    skipped: list[dict] = []
    seen_contents: dict[str, str] = {}

    for name, content in files:
        raw = content.encode("utf-8") if isinstance(content, str) else content
        digest = hashlib.sha256(raw).hexdigest()
        if digest in seen_contents:
            skipped.append({"file": name, "reason": f"כפילות של הקובץ {seen_contents[digest]}"})
            continue
        seen_contents[digest] = name

        try:
            tracks = parse_mislaka_file(content)
        except Exception as exc:  # a malformed file must not abort the whole batch
            errors.append({"file": name, "error": _describe_parse_error(exc)})
            continue

        holdings = []
        for mislaka, fund in find_matching_funds(tracks, universe.all_funds):
            holding = compare_holding(mislaka, fund, universe, weights, override_risk_level, pools)
            if holding is not None:
                holdings.append((mislaka, holding))
        if not holdings:
            skipped.append({"file": name, "reason": "לא נמצאו בקובץ קופות גמל או השתלמות מגמל נט"})
            continue

        for mislaka, holding in holdings:
            client_id = mislaka.get("MISPAR-ZIHUY-LAKOACH", "unknown")
            known = client_id != "unknown"
            entry = clients.setdefault(
                client_id if known else f"file:{name}",
                {"client_id": client_id if known else None, "client_name": "", "files": [], "funds": []},
            )
            entry["client_name"] = entry["client_name"] or mislaka.get("SHEM-LAKOACH", "")
            if name not in entry["files"]:
                entry["files"].append(name)
            entry["funds"].append(holding)

    ranked = [{**entry, "portfolio": summarize_portfolio(entry["funds"])} for entry in clients.values()]
    ranked.sort(key=_urgency_key)
    return {"clients": ranked, "errors": errors, "skipped": skipped, "files_received": len(files)}
