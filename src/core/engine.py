"""Comparison engine that ranks pension/provident funds for a given client portfolio."""

# ----- Imports ----- #

import copy
from pathlib import Path
from typing import Optional


from src.core import risk_classifier
from src.parsers.fund_parser import parse_xml_file
from src.parsers.mislaka_parser import parse_multible_mislaka_files

# ----- Constants ----- #

_DATA_DIR = Path(__file__).parent.parent.parent / "data"
GEMEL_NET_PATH = _DATA_DIR / "kupot_gemel_net.xml"
RISKS_MAP_PATH = _DATA_DIR / "risks_map.xml"

# Fixed default weights used for community comparisons (fair, user-independent)
DEFAULT_WEIGHT_1 = 10
DEFAULT_WEIGHT_3 = 20
DEFAULT_WEIGHT_5 = 25
DEFAULT_WEIGHT_SHARP = 45

# Parse static data once at startup
risk_classifier.load(RISKS_MAP_PATH)

# ----- Functions ----- #


def find_matching_funds(
    mislaka_list: list[dict], funds_list: list[dict]
) -> list[tuple[dict, dict]]:
    """Match each Mislaka entry to its corresponding fund in the GemeNet list.

    Args:
        mislaka_list: Parsed records from one or more Mislaka XML files.
        funds_list: Full list of fund records from the GemeNet XML file.

    Returns:
        A list of ``(mislaka_record, fund_record)`` pairs where the GemeNet ID
        found in the Mislaka record exists in the fund lookup table.
    """
    funds_by_id = {fund["ID"]: fund for fund in funds_list}
    return [
        (mislaka, funds_by_id[mislaka["GEMELNET_ID"]])
        for mislaka in mislaka_list
        if mislaka["GEMELNET_ID"] in funds_by_id
    ]


def get_funds_by_risk_level(funds_list: list[dict], risk_level: str) -> list[dict]:
    """Filter a list of funds to only those matching the given risk level.

    Args:
        funds_list: List of fund dicts, each containing a ``risk_level`` key.
        risk_level: The target risk level string (e.g. ``"low"``, ``"medium"``,
            ``"high"``).

    Returns:
        A filtered list of fund dicts whose ``risk_level`` equals *risk_level*.
    """
    return [fund for fund in funds_list if fund["risk_level"] == risk_level]


def apply_dmey_nihul(funds_list: list[dict], dmey_nihul: float) -> list[dict]:
    """Subtract management fees from the return fields of each fund in-place.

    Only subtracts when the return value is positive, to avoid distorting funds
    with missing or zero data.

    Args:
        funds_list: List of fund dicts to adjust (modified in-place).
        dmey_nihul: Annual management-fee percentage to deduct.

    Returns:
        The same list with adjusted return values.
    """
    for fund in funds_list:
        if fund["tsua_5"] > 0.0:
            fund["tsua_5"] -= dmey_nihul
        if fund["tsua_3"] > 0.0:
            fund["tsua_3"] -= dmey_nihul
        if fund["tsua_mitztaberet_letkufa"] > 0.0:
            fund["tsua_mitztaberet_letkufa"] -= dmey_nihul
    return funds_list


def normalize_data(funds_list: list[dict]) -> None:
    """Add min-max normalised variants (0–100) of the key performance fields.

    For each of the four performance fields, a new ``<field>_normalized`` key
    is added to every fund dict.  Funds with a raw value of ``0.0`` receive a
    normalised score of ``0.0`` without affecting the normalisation range.

    Args:
        funds_list: List of fund dicts to enrich with normalised fields
            (modified in-place).
    """
    fields = [
        "sharp_ribit_hasarot_sikun",
        "tsua_5",
        "tsua_3",
        "tsua_mitztaberet_letkufa",
    ]
    for field in fields:
        values = [fund[field] for fund in funds_list if fund[field] != 0.0]
        if not values:
            for fund in funds_list:
                fund[field + "_normalized"] = 0.0
            continue
        min_value = min(values)
        max_value = max(values)
        for fund in funds_list:
            if fund[field] != 0.0:
                fund[field + "_normalized"] = (
                    (fund[field] - min_value) / (max_value - min_value) * 100
                    if max_value > min_value
                    else 0.0
                )
            else:
                fund[field + "_normalized"] = 0.0


def calculate_grade(
    fund: dict,
    weight_1: int,
    weight_3: int,
    weight_5: int,
    weight_sharp: int,
) -> float:
    """Compute a weighted composite score for a single fund.

    All four normalised metrics must be non-zero for a grade to be calculated;
    otherwise ``0`` is returned to indicate insufficient data.

    Args:
        fund: Fund dict that already contains normalised performance fields.
        weight_1: Weight for the 1-year cumulative return (normalised).
        weight_3: Weight for the 3-year average annual return (normalised).
        weight_5: Weight for the 5-year average annual return (normalised).
        weight_sharp: Weight for the Sharpe ratio (normalised).

    Returns:
        A weighted composite score rounded to two decimal places, or ``0`` if
        any of the required normalised fields are zero.
    """
    weights = {}

    if fund.get("tsua_mitztaberet_letkufa_normalized") != 0.0:
        weights["tsua_mitztaberet_letkufa_normalized"] = weight_1
    if fund.get("tsua_3_normalized") != 0.0:
        weights["tsua_3_normalized"] = weight_3
    if fund.get("tsua_5_normalized") != 0.0:
        weights["tsua_5_normalized"] = weight_5
    if fund.get("sharp_ribit_hasarot_sikun_normalized") != 0.0:
        weights["sharp_ribit_hasarot_sikun_normalized"] = weight_sharp

    if not weights:
        return 0
    total_weight = sum(weights.values())
    if total_weight != 100:
        return 0
    grade = 0
    for field, weight in weights.items():
        grade += fund[field] * (weight / total_weight)
    return round(grade, 2)


def add_grade_and_sort(
    funds_list: list[dict],
    weight_1: int,
    weight_3: int,
    weight_5: int,
    weight_sharp: int,
) -> list[dict]:
    """Assign a composite grade to each fund and return them sorted descending.

    Args:
        funds_list: List of fund dicts with normalised performance fields.
        weight_1: Weight for the 1-year cumulative return metric.
        weight_3: Weight for the 3-year average annual return metric.
        weight_5: Weight for the 5-year average annual return metric.
        weight_sharp: Weight for the Sharpe ratio metric.

    Returns:
        The same list sorted from highest grade to lowest, with a ``grade``
        key added to every fund dict.
    """
    for fund in funds_list:
        fund["grade"] = calculate_grade(fund, weight_1, weight_3, weight_5, weight_sharp)

    return sorted(funds_list, key=lambda x: x["grade"], reverse=True)


def get_top_3(sorted_funds: list[dict]) -> list[dict]:
    """Return the top three funds from an already-sorted list.

    Args:
        sorted_funds: Funds list sorted from best to worst grade.

    Returns:
        The first three elements of *sorted_funds* (fewer if the list is
        shorter than three).
    """
    return sorted_funds[:3]


def get_client_ranking(
    sorted_funds: list[dict], client_fund_id: str
) -> tuple[Optional[int], int]:
    """Find the 1-based rank of the client's fund within a sorted list.

    Args:
        sorted_funds: Funds list sorted from best to worst grade.
        client_fund_id: The ``ID`` string of the client's current fund.

    Returns:
        A tuple of ``(rank, total)`` where *rank* is the 1-based position of
        the client's fund (or ``None`` if not found) and *total* is the length
        of *sorted_funds*.
    """
    for i, fund in enumerate(sorted_funds):
        if fund["ID"] == client_fund_id:
            return i + 1, len(sorted_funds)
    return None, len(sorted_funds)


def calculate_potential_amount(
    current_amount: float, current_fund: dict, better_fund: dict,
    field: str = "tsua_mitztaberet_letkufa",
    years: int = 1,
) -> float:
    """Answer: "If I had migrated to the better fund N years ago, how much would I have today?"

    Back-calculates the client's starting balance N years ago (by reversing the
    current fund's return), then grows that same starting balance at the better
    fund's historical rate for N years to produce a "today" value.

    Equivalent formula:  current_amount × (1 + better_return%)^N
                                         ──────────────────────────
                                          (1 + current_return%)^N

    Args:
        current_amount: The client's current accumulated savings balance.
        current_fund: Dict for the client's current fund.
        better_fund: Dict for the comparison fund.
        field: Return field to use (default: 1-year cumulative return).
        years: How many years back to project (1 → 1-year return, 3 → 3-year, 5 → 5-year).

    Returns:
        What the balance would be today had the client been in the better fund
        for the past *years* years, rounded to two decimal places.
    """
    current_return = current_fund[field]
    better_return = better_fund[field]
    denominator = (1 + current_return / 100) ** years
    if denominator == 0:
        return round(current_amount, 2)
    potential = current_amount * (1 + better_return / 100) ** years / denominator
    return round(potential, 2)


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
    all_funds = parse_xml_file(GEMEL_NET_PATH, low_exposure_threshold, medium_exposure_threshold, [], remove_special_cases=False)
    funds_to_suggest = parse_xml_file(GEMEL_NET_PATH, low_exposure_threshold, medium_exposure_threshold, bad_hevrot, remove_special_cases=True)
    mislaka_list = parse_multible_mislaka_files(mislaka_file)
    matches = find_matching_funds(mislaka_list, all_funds)
    funds_list = []
    for mislaka, fund in matches:
        sug = fund["SUG"]
        funds_to_suggest.append(fund)
        our_funds = [f for f in funds_to_suggest if f["SUG"] == sug]
        risk_level = fund["risk_level"]
        comparison_risk_level = override_risk_level if override_risk_level else risk_level
        dmey_nihul = mislaka["SHEUR-DMEI-NIHUL-TZVIRA"]
        all_funds_in_risk_level = get_funds_by_risk_level(our_funds, comparison_risk_level)
        if override_risk_level and not any(f["ID"] == fund["ID"] for f in all_funds_in_risk_level):
            client_base = next((f for f in our_funds if f["ID"] == fund["ID"]), fund)
            all_funds_in_risk_level = [client_base] + all_funds_in_risk_level
        adjusted_funds = apply_dmey_nihul(copy.deepcopy(all_funds_in_risk_level), dmey_nihul)
        normalize_data(adjusted_funds)
        sorted_funds = add_grade_and_sort(adjusted_funds, weight_1, weight_3, weight_5, weight_sharp)
        client_ranking, total_funds = get_client_ranking(sorted_funds, fund["ID"])
        for i in sorted_funds:
            if i["ID"] == fund["ID"]:
                client_fund = i
                break
        default_sorted = add_grade_and_sort(
            copy.deepcopy(adjusted_funds),
            DEFAULT_WEIGHT_1, DEFAULT_WEIGHT_3, DEFAULT_WEIGHT_5, DEFAULT_WEIGHT_SHARP,
        )
        for i in default_sorted:
            if i["ID"] == fund["ID"]:
                default_client_fund = i
                break
        money = mislaka["TOTAL-CHISACHON-MTZBR"]
        if money == 0:
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
                golden_adjusted_funds = apply_dmey_nihul(copy.deepcopy(all_funds_in_high_risk_level), dmey_nihul)
                normalize_data(golden_adjusted_funds)
                golden_sorted_funds = add_grade_and_sort(
                    golden_adjusted_funds, weight_1, weight_3, weight_5, weight_sharp
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
