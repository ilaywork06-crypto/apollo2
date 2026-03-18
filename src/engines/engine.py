# ----- Imports ----- #

import copy

from src.parsers.mislaka_parser import parse_multible_mislaka_files
from src.parsers.parser import parse_xml_file
from src.parsers.risk_level_generator import get_stocks_percentage_by_kupa_id

# ----- Constants ----- #

GEMEL_NET_PATH = "/Users/msphttyh/Documents/apolo/apollo2/src/engines/kupot_gemel_net.xml"


RISKS_MAP_PATH = "/Users/msphttyh/Documents/apolo/apollo2/src/engines/risks_map.xml"

# ----- Functions ----- #


def find_matching_kupot(mislaka_list, kupot_list):
    matches = []
    for mislaka in mislaka_list:
        for kupa in kupot_list:
            if mislaka["GEMELNET_ID"] == kupa["ID"]:
                matches.append((mislaka, kupa))

    return matches


def get_kupot_by_risk_level(kupot_list, risk_level):
    return [kupa for kupa in kupot_list if kupa["risk_level"] == risk_level]


def apply_dmey_nihul(kupot_list, dmey_nihul):
    for kupa in kupot_list:
        if kupa["tsua_5"] > 0.0:
            kupa["tsua_5"] -= dmey_nihul
        if kupa["tsua_3"] > 0.0:
            kupa["tsua_3"] -= dmey_nihul
        if kupa["tsua_mitztaberet_letkufa"] > 0.0:
            kupa["tsua_mitztaberet_letkufa"] -= dmey_nihul
    return kupot_list


def normalize_data(kupot_list):
    fields = [
        "sharp_ribit_hasarot_sikun",
        "tsua_5",
        "tsua_3",
        "tsua_mitztaberet_letkufa",
    ]
    for field in fields:
        values = [kupa[field] for kupa in kupot_list if kupa[field] != 0.0]
        min_value = min(values)
        max_value = max(values)
        for kupa in kupot_list:
            if kupa[field] != 0.0:
                kupa[field + "_normalized"] = (
                    (kupa[field] - min_value) / (max_value - min_value) * 100
                    if max_value > min_value
                    else 0.0
                )
            else:
                kupa[field + "_normalized"] = 0.0


def calculate_grade(
    kupa,
    weight_1,
    weight_3,
    weight_5,
    weight_sharp,
    ):
    weights = {}

    if kupa.get("tsua_mitztaberet_letkufa_normalized") != 0.0:
        if kupa.get("tsua_3_normalized") != 0.0:
            if kupa.get("tsua_5_normalized") != 0.0:
                if kupa.get("sharp_ribit_hasarot_sikun_normalized") != 0.0:
                    weights["tsua_mitztaberet_letkufa_normalized"] = weight_1
                    weights["sharp_ribit_hasarot_sikun_normalized"] = weight_sharp
                    weights["tsua_5_normalized"] = weight_5
                    weights["tsua_3_normalized"] = weight_3

    if not weights or len(weights) != 4:
        return 0

    total_weight = sum(weights.values())
    grade = 0
    for field, weight in weights.items():
        grade += kupa[field] * (weight / total_weight)

    return round(grade, 2)


def add_grade_and_sort(
    kupot_list,
    weight_1,
    weight_3,
    weight_5,
    weight_sharp,
    ):
    for kupa in kupot_list:
        kupa["grade"] = calculate_grade(
            kupa,
            weight_1,
            weight_3,
            weight_5,
            weight_sharp,
        )

    return sorted(
        kupot_list,
        key=lambda x: x["grade"],
        reverse=True,
    )


def get_top_3(sorted_kupot):
    return sorted_kupot[:3]


def get_client_ranking(sorted_kupot, client_kupa_id):
    for i, kupa in enumerate(sorted_kupot):
        if kupa["ID"] == client_kupa_id:
            return i + 1, len(sorted_kupot)
    return None, len(sorted_kupot)


def calculate_potential_amount(
    current_amount,
    current_kupa,
    better_kupa,
    ):
    diff = better_kupa["tsua_mitztaberet_letkufa"] - current_kupa["tsua_mitztaberet_letkufa"]
    potential = current_amount * (1 + diff / 100)
    return round(potential, 2)

def filter_koput_by_sug(kupot_list, sug):
    output = []
    for kupa in kupot_list:
        SUG_KUPA = kupa["SUG"]
        if SUG_KUPA == sug:
            output.append(kupa)
    return output

def run_comparison(
    mislaka_file,
    weight_1,
    weight_3,
    weight_5,
    weight_sharp,
    ):
    get_stocks_percentage_by_kupa_id(RISKS_MAP_PATH)
    funds_list = []
    kupot_list = parse_xml_file(GEMEL_NET_PATH)
    mislaka_list = parse_multible_mislaka_files(mislaka_file)
    matches = find_matching_kupot(mislaka_list, kupot_list)
    output = []
    for mislaka, kupa in matches:
        sug = kupa["SUG"]
        our_koput = filter_koput_by_sug(kupot_list, sug)
        risk_level = kupa["risk_level"]
        golden = {}
        dmey_nihul = mislaka["SHEUR-DMEI-NIHUL-TZVIRA"]
        all_kopot_in_risk_level = get_kupot_by_risk_level(our_koput, risk_level)
        adjusted_kupot = apply_dmey_nihul(copy.deepcopy(all_kopot_in_risk_level), dmey_nihul)
        normalize_data(adjusted_kupot)
        sorted_kupot = add_grade_and_sort(
            adjusted_kupot,
            weight_1,
            weight_3,
            weight_5,
            weight_sharp,
        )
        top_3 = get_top_3(sorted_kupot)
        client_ranking, total_kupot = get_client_ranking(sorted_kupot, kupa["ID"])
        client_kupa = next(k for k in sorted_kupot if k["ID"] == kupa["ID"])
        money = mislaka["TOTAL-CHISACHON-MTZBR"]
        if money == 0:
            continue
        kupa_rank = 1
        client = {
            "name": client_kupa["shem_kupa"],
            "id": client_kupa["ID"],
            "grade": client_kupa["grade"],
            "rank": client_ranking,
            "total_in_risk": total_kupot,
            "risk_level": risk_level,
            "amount": money,
            "dmei_nihul": dmey_nihul,
            "tsua_1": round(client_kupa["tsua_mitztaberet_letkufa"], 2),
            "tsua_3": round(client_kupa["tsua_3"], 2),
            "tsua_5": round(client_kupa["tsua_5"], 2),
            "hevra": client_kupa["hevra"],
            "seniority_date": mislaka["TAARICH-HITZTARFUT-MUTZAR"],
            "percentile": round((total_kupot - client_ranking) / total_kupot * 100),
        }
        if risk_level != "high":
            all_koput_in_high_risk_level = get_kupot_by_risk_level(our_koput, "high")
            golden_adjusted_koput = apply_dmey_nihul(copy.deepcopy(all_koput_in_high_risk_level), dmey_nihul)
            normalize_data(golden_adjusted_koput)
            golden_sorted_kupot = add_grade_and_sort(
            golden_adjusted_koput,
            weight_1,
            weight_3,
            weight_5,
            weight_sharp,
        )
            gold_3 = get_top_3(golden_sorted_kupot)
            better_gold = gold_3[1]
            potential_amount_gold = calculate_potential_amount(
                    money,
                    client_kupa,
                    better_gold,
            )
            golden = {
                "name": better_gold["shem_kupa"],
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
            }
        alternatives = []
        for better_kupa in top_3:
            if better_kupa["ID"] != client_kupa["ID"]:
                potential_amount = calculate_potential_amount(
                    money,
                    client_kupa,
                    better_kupa,
                )
                output.append(
                    {
                        "client": f"Client's Kupa: {client_kupa['shem_kupa']}, Kupa id: {client_kupa['ID']} - (Grade: {client_kupa['grade']}, Rank - {client_ranking}/{total_kupot})",
                        "alternative": f"Better Kupa: {better_kupa['shem_kupa']}, Kupa id : {better_kupa['ID']} - (Grade: {better_kupa['grade']}), Rank - {kupa_rank}/{total_kupot}",
                        "amount": f"Current amount: {money}",
                        "potential": f"Potential amount after switching: {potential_amount} NIS\n",
                    }
                )
                alt = {
                    "name": better_kupa["shem_kupa"],
                    "id": better_kupa["ID"],
                    "grade": better_kupa["grade"],
                    "rank": kupa_rank,
                    "hevra": better_kupa["hevra"],
                    "tsua_1": round(better_kupa["tsua_mitztaberet_letkufa"], 2),
                    "tsua_3": round(better_kupa["tsua_3"], 2),
                    "tsua_5": round(better_kupa["tsua_5"], 2),
                    "potential_amount": potential_amount,
                    "diff": round(potential_amount - money, 2),
                    "diff_percent": round((potential_amount - money) / money * 100, 1),
                }
                alternatives.append(alt)
                kupa_rank += 1
            else:
                kupa_rank += 1
        funds_list.append({"client": client, "alternatives": alternatives, "golden":golden})

    return {"funds": funds_list}
