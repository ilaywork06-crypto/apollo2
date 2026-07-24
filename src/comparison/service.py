"""Orchestrates the full fund comparison for all holdings in a client's Mislaka files."""

import copy

from src.comparison.config import (
    DEFAULT_WEIGHT_1,
    DEFAULT_WEIGHT_3,
    DEFAULT_WEIGHT_5,
    DEFAULT_WEIGHT_SHARP,
    GEMEL_NET_PATH,
    RISKS_MAP_PATH,
)
from src.comparison.filters import remove_bad_hevrot
from src.comparison.grading import add_grade_and_sort, get_top_3
from src.comparison.matching import find_matching_funds, get_funds_by_risk_level
from src.comparison.pool import build_graded_pool
from src.comparison.projections import calculate_potential_amount
from src.comparison.ranking import get_client_ranking
from src.comparison.risk_classifier import RiskClassifier
from src.parsers.fund_parser import parse_xml_file
from src.parsers.mislaka.parser import parse_multible_mislaka_files
from src.parsers.mislaka.track_extractor import MIN_TRACK_BALANCE


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
) -> dict:
    """Orchestrate the full fund comparison for all holdings in the Mislaka files.

    For each matched holding the function:
    * filters peer funds by fund type and risk level,
    * applies the client's management fee,
    * normalises and grades every peer,
    * builds a response payload with the client's fund details, ranked
      alternatives at the same risk level, and (if applicable) the best
      available high-risk fund as a ``golden`` option.

    Args:
        mislaka_file: List of decoded Mislaka XML file strings.
        weight_1: Weight for the 1-year cumulative return metric.
        weight_3: Weight for the 3-year average annual return metric.
        weight_5: Weight for the 5-year average annual return metric.
        weight_sharp: Weight for the Sharpe ratio metric.

    Returns:
        A dict with a ``funds`` key containing a list of per-holding result
        dicts, each with ``client``, ``alternatives``, and ``golden`` keys.
    """
    risk_classifier = RiskClassifier(path=RISKS_MAP_PATH)
    all_funds = parse_xml_file(
        GEMEL_NET_PATH, low_exposure_threshold, medium_exposure_threshold,
        risk_classifier=risk_classifier, remove_special_cases=False,
    )
    funds_to_suggest = remove_bad_hevrot(
        parse_xml_file(
            GEMEL_NET_PATH, low_exposure_threshold, medium_exposure_threshold,
            risk_classifier=risk_classifier, remove_special_cases=True,
        ),
        bad_hevrot,
    )
    mislaka_list = parse_multible_mislaka_files(mislaka_file)
    matches = find_matching_funds(mislaka_list, all_funds)
    funds_list = []
    for mislaka, fund in matches:
        sug = fund["SUG"]
        funds_to_suggest.append(fund)
        our_funds = [f for f in funds_to_suggest if f["SUG"] == sug]
        risk_level = fund["risk_level"]
        comparison_risk_level = override_risk_level if override_risk_level else risk_level
        dmey_nihul = mislaka["SHEUR-DMEI-NIHUL-HISACHON-MIVNE"]
        all_funds_in_risk_level = get_funds_by_risk_level(our_funds, comparison_risk_level)
        if override_risk_level and not any(f["ID"] == fund["ID"] for f in all_funds_in_risk_level):
            client_base = next((f for f in our_funds if f["ID"] == fund["ID"]), fund)
            all_funds_in_risk_level = [client_base] + all_funds_in_risk_level
        sorted_funds = build_graded_pool(
            all_funds_in_risk_level, dmey_nihul, weight_1, weight_3, weight_5, weight_sharp
        )
        client_ranking, total_funds = get_client_ranking(sorted_funds, fund["ID"])
        for i in sorted_funds:
            if i["ID"] == fund["ID"]:
                client_fund = i
                break
        default_sorted = add_grade_and_sort(
            copy.deepcopy(sorted_funds),
            DEFAULT_WEIGHT_1, DEFAULT_WEIGHT_3, DEFAULT_WEIGHT_5, DEFAULT_WEIGHT_SHARP,
        )
        for i in default_sorted:
            if i["ID"] == fund["ID"]:
                default_client_fund = i
                break
        money = mislaka["TOTAL-CHISACHON-MTZBR"]
        if money < MIN_TRACK_BALANCE:
            continue

        client = {
            "name": client_fund["fund_name"],
            "id": client_fund["ID"],
            "client_id": mislaka.get("MISPAR-ZIHUY-LAKOACH", "unknown"),
            "grade": client_fund["grade"],
            "default_grade": default_client_fund["grade"],
            "rank": client_ranking,
            "total_in_risk": total_funds,
            "risk_level": risk_level,
            "amount": money,
            "dmei_nihul": dmey_nihul,
            "tsua_1": round(client_fund["tsua_mitztaberet_letkufa"], 2),
            "tsua_3": round(client_fund["tsua_3"], 2),
            "tsua_5": round(client_fund["tsua_5"], 2),
            "hevra": client_fund["hevra"],
            "seniority_date": mislaka["TAARICH-HITZTARFUT-MUTZAR"],
            "percentile": round((total_funds - client_ranking) / total_funds * 100),
            "equity_exposure": client_fund.get("equity_exposure"),
        }

        golden = {}
        if override_risk_level is None and risk_level != "high":
            all_funds_in_high_risk_level = get_funds_by_risk_level(our_funds, "high")
            if all_funds_in_high_risk_level:
                golden_sorted_funds = build_graded_pool(
                    all_funds_in_high_risk_level, dmey_nihul, weight_1, weight_3, weight_5, weight_sharp
                )
                better_gold = get_top_3(golden_sorted_funds)[0]
                potential_amount_gold   = calculate_potential_amount(money, client_fund, better_gold, field="tsua_mitztaberet_letkufa", years=1)
                potential_amount_gold_3 = calculate_potential_amount(money, client_fund, better_gold, field="tsua_3", years=3)
                potential_amount_gold_5 = calculate_potential_amount(money, client_fund, better_gold, field="tsua_5", years=5)
                best_same_risk = next((f for f in sorted_funds if f["ID"] != client_fund["ID"]), None)
                best_same_risk_potential = calculate_potential_amount(money, client_fund, best_same_risk) if best_same_risk else 0
                if potential_amount_gold > best_same_risk_potential:
                    golden = {
                        "name": better_gold["fund_name"],
                        "id": better_gold["ID"],
                        "grade": better_gold["grade"],
                        "rank": 1,
                        "hevra": better_gold["hevra"],
                        "tsua_1": round(better_gold["tsua_mitztaberet_letkufa"], 2),
                        "tsua_3": round(better_gold["tsua_3"], 2),
                        "tsua_5": round(better_gold["tsua_5"], 2),
                        "potential_amount": potential_amount_gold,
                        "diff": round(potential_amount_gold - money, 2),
                        "diff_percent": round((potential_amount_gold - money) / money * 100, 1),
                        "potential_amount_3": potential_amount_gold_3,
                        "diff_3": round(potential_amount_gold_3 - money, 2),
                        "diff_percent_3": round((potential_amount_gold_3 - money) / money * 100, 1),
                        "potential_amount_5": potential_amount_gold_5,
                        "diff_5": round(potential_amount_gold_5 - money, 2),
                        "diff_percent_5": round((potential_amount_gold_5 - money) / money * 100, 1),
                    }

        alternatives = []
        fund_rank = 1
        for better_fund in sorted_funds:
            if len(alternatives) >= 3:
                break
            if better_fund["ID"] != client_fund["ID"]:
                potential_amount   = calculate_potential_amount(money, client_fund, better_fund, field="tsua_mitztaberet_letkufa", years=1)
                potential_amount_3 = calculate_potential_amount(money, client_fund, better_fund, field="tsua_3", years=3)
                potential_amount_5 = calculate_potential_amount(money, client_fund, better_fund, field="tsua_5", years=5)
                alt = {
                    "name": better_fund["fund_name"],
                    "id": better_fund["ID"],
                    "grade": better_fund["grade"],
                    "rank": fund_rank,
                    "hevra": better_fund["hevra"],
                    "tsua_1": round(better_fund["tsua_mitztaberet_letkufa"], 2),
                    "tsua_3": round(better_fund["tsua_3"], 2),
                    "tsua_5": round(better_fund["tsua_5"], 2),
                    "potential_amount": potential_amount,
                    "diff": round(potential_amount - money, 2),
                    "diff_percent": round((potential_amount - money) / money * 100, 1),
                    "potential_amount_3": potential_amount_3,
                    "diff_3": round(potential_amount_3 - money, 2),
                    "diff_percent_3": round((potential_amount_3 - money) / money * 100, 1),
                    "potential_amount_5": potential_amount_5,
                    "diff_5": round(potential_amount_5 - money, 2),
                    "diff_percent_5": round((potential_amount_5 - money) / money * 100, 1),
                }
                alternatives.append(alt)
            fund_rank += 1

        funds_list.append({"client": client, "alternatives": alternatives, "golden": golden})
        funds_to_suggest.remove(fund)

    return {"funds": funds_list}
